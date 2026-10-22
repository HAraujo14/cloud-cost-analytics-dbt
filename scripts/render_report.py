"""Render a markdown and HTML summary from the local warehouse.

The report repeats figures computed from the synthetic marts. It is a
notebook-free artifact for the portfolio, not a billing dashboard.
"""

from __future__ import annotations

import html
import json
from datetime import date, datetime

import duckdb
import pandas as pd

from scripts.paths import FORECAST_CSV, FORECAST_META, REPORT_HTML, REPORT_MD, WAREHOUSE_PATH

DATASET_LABEL = "synthetic-finops-portfolio"


def main() -> None:
    if not WAREHOUSE_PATH.exists():
        raise SystemExit(f"Missing {WAREHOUSE_PATH}. Run `dbt build` first.")
    if not FORECAST_CSV.exists() or not FORECAST_META.exists():
        raise SystemExit("Missing forecast output. Run `python -m scripts.forecast_cost` first.")

    connection = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        report = _build_report(connection)
    finally:
        connection.close()
    REPORT_MD.parent.mkdir(parents=True, exist_ok=True)
    REPORT_MD.write_text(report["markdown"])
    REPORT_HTML.write_text(report["html"])
    print(f"Wrote {REPORT_MD}")
    print(f"Wrote {REPORT_HTML}")


def _build_report(connection: duckdb.DuckDBPyConnection) -> dict[str, str]:
    window = connection.execute(
        """
        select
            min(usage_date) as start_date,
            max(usage_date) as end_date,
            count(*) as fact_rows,
            sum(net_cost) as net_cost,
            sum(gross_cost) as gross_cost,
            sum(credit_amount) as credit_amount
        from marts.fct_daily_cost
        """
    ).fetchone()
    assert window is not None
    start_date, end_date, fact_rows, net_cost, gross_cost, credit_amount = window
    latest_month = connection.execute(
        "select max(billing_month) from marts.fct_daily_cost"
    ).fetchone()
    assert latest_month is not None
    billing_month = latest_month[0]

    by_cloud = _frame(
        connection,
        """
        select cloud_provider, sum(net_cost) as net_cost, sum(gross_cost) as gross_cost
        from marts.fct_daily_cost
        group by 1
        order by 1
        """,
    )
    row_counts = _frame(
        connection,
        """
        select 'aws_cur' as extract_name, count(*) as rows from staging.stg_aws_cur
        union all
        select 'gcp_billing' as extract_name, count(*) as rows from staging.stg_gcp_billing
        order by 1
        """,
    )
    by_team = _frame(
        connection,
        """
        select team, sum(net_cost) as net_cost
        from marts.fct_cost_by_team
        where billing_month = ?
        group by 1
        order by net_cost desc
        """,
        [billing_month],
    )
    top_services = _frame(
        connection,
        """
        select cloud_provider, service_name, sum(net_cost) as net_cost
        from marts.fct_daily_cost
        where billing_month = ?
        group by 1, 2
        order by net_cost desc
        limit 8
        """,
        [billing_month],
    )
    movers = _frame(
        connection,
        """
        select
            cloud_provider,
            service_name,
            sum(net_cost) as net_cost,
            sum(prev_month_net_cost) as prev_month_net_cost
        from marts.fct_cost_mom
        where billing_month = ?
        group by 1, 2
        order by abs(sum(net_cost) - sum(prev_month_net_cost)) desc
        limit 8
        """,
        [billing_month],
    )
    anomalies = _frame(
        connection,
        """
        select
            usage_date,
            cloud_provider,
            account_name,
            service_name,
            net_cost,
            rolling_mean_cost,
            z_score,
            labelled_spike_id
        from marts.mart_service_anomalies
        where is_cost_spike
        order by z_score desc
        """,
    )
    detection = connection.execute(
        """
        select
            count(*) filter (where labelled_spike_id is not null) as labelled_days,
            count(*) filter (
                where labelled_spike_id is not null and is_cost_spike
            ) as labelled_and_flagged,
            count(*) filter (where is_cost_spike) as flagged_days,
            count(*) filter (
                where is_cost_spike and labelled_spike_id is null
            ) as flagged_unlabelled
        from marts.mart_service_anomalies
        """
    ).fetchone()
    assert detection is not None
    unit_costs = _frame(
        connection,
        """
        select
            service_name,
            usage_type,
            usage_unit,
            sum(gross_cost) / nullif(sum(usage_amount), 0) as gross_unit_cost,
            sum(net_cost) / nullif(sum(usage_amount), 0) as net_unit_cost
        from marts.fct_unit_cost
        where billing_month = ?
        group by 1, 2, 3
        having sum(usage_amount) > 0
        order by sum(net_cost) desc
        limit 8
        """,
        [billing_month],
    )
    forecast = pd.read_csv(FORECAST_CSV)
    meta = json.loads(FORECAST_META.read_text())

    context = {
        "start_date": _as_date(start_date),
        "end_date": _as_date(end_date),
        "fact_rows": int(fact_rows),
        "net_cost": float(net_cost),
        "gross_cost": float(gross_cost),
        "credit_amount": float(credit_amount),
        "billing_month": _as_date(billing_month),
        "by_cloud": by_cloud,
        "row_counts": row_counts,
        "by_team": by_team,
        "top_services": top_services,
        "movers": movers,
        "anomalies": anomalies,
        "detection": detection,
        "unit_costs": unit_costs,
        "forecast": forecast,
        "meta": meta,
    }
    return {"markdown": _markdown(context), "html": _html(context)}


def _markdown(context: dict[str, object]) -> str:
    detection = context["detection"]
    assert isinstance(detection, tuple)
    lines = [
        "# Synthetic cloud cost summary",
        "",
        "> Synthetic data (`synthetic-finops-portfolio`). These figures are",
        "> computed from the generated extract. They are not real cloud spend.",
        "",
        "## Window",
        "",
        f"- Usage dates: {context['start_date']} through {context['end_date']}",
        f"- Daily fact rows: {context['fact_rows']:,}",
        f"- Gross cost: {_money(context['gross_cost'])}",
        f"- Credits (positive magnitude): {_money(context['credit_amount'])}",
        f"- Net cost: {_money(context['net_cost'])}",
        "",
        "Extract row counts:",
        "",
        _md_table(
            ["extract", "rows"],
            [[row.extract_name, f"{int(row.rows):,}"] for row in _rows(context["row_counts"])],
        ),
        "",
        "Net cost by cloud, full window:",
        "",
        _md_table(
            ["cloud", "net cost", "gross cost"],
            [
                [row.cloud_provider, _money(row.net_cost), _money(row.gross_cost)]
                for row in _rows(context["by_cloud"])
            ],
        ),
        "",
        f"## Latest month ({context['billing_month']:%Y-%m})",
        "",
        "Net cost by team:",
        "",
        _md_table(
            ["team", "net cost"],
            [[row.team, _money(row.net_cost)] for row in _rows(context["by_team"])],
        ),
        "",
        "Largest services:",
        "",
        _md_table(
            ["cloud", "service", "net cost"],
            [
                [row.cloud_provider, row.service_name, _money(row.net_cost)]
                for row in _rows(context["top_services"])
            ],
        ),
        "",
        "Largest month-over-month service moves (summed across accounts):",
        "",
        _md_table(
            ["cloud", "service", "this month", "prior month", "change"],
            [_mover_row(row) for row in _rows(context["movers"])],
        ),
        "",
        "## Anomaly screen",
        "",
        "Rolling 28-day z-score of daily net cost by account and service.",
        "A day is flagged when at least 14 prior days exist, z >= 3,",
        "and net cost is at least 25% above the trailing mean.",
        "On this generated dataset:",
        "",
        f"- Labelled spike account-service-days: {int(detection[0])}",
        f"- Of those, flagged by the screen: {int(detection[1])}",
        f"- Flagged days in total: {int(detection[2])}",
        f"- Flagged days with no injected spike label: {int(detection[3])}",
        "",
        "Flagged days, highest z-score first:",
        "",
        _md_table(
            ["date", "cloud", "account", "service", "net cost", "baseline", "z", "spike"],
            [_anomaly_row(row) for row in _rows(context["anomalies"])],
        ),
        "",
        "## Unit cost",
        "",
        "Spikes in this dataset scale usage and price together, so unit cost",
        "stays near the anchor rate. Credits lower the net unit cost.",
        f"Averages for {context['billing_month']:%Y-%m}, largest services first:",
        "",
        _md_table(
            ["service", "usage type", "unit", "gross unit cost", "net unit cost"],
            [
                [
                    row.service_name,
                    row.usage_type,
                    row.usage_unit,
                    f"{float(row.gross_unit_cost):.6f}",
                    f"{float(row.net_unit_cost):.6f}",
                ]
                for row in _rows(context["unit_costs"])
            ],
        ),
        "",
        "## Forecast",
        "",
        "Method: OLS trend plus an additive weekday residual.",
        "Spike days flagged above are left out of the fit.",
        "The band is +/- 1.96 residual standard deviations.",
        "It is illustrative, not a calibrated prediction interval.",
        "Holdout MAPE is only a backtest on this synthetic series.",
        "",
        _md_table(
            ["series", "holdout MAPE", "MAPE excluding spike days", "slope per day"],
            [_metric_row(item) for item in _meta_series(context)],
        ),
        "",
        "Next 7 forecast days:",
        "",
        _md_table(
            ["series", "date", "forecast net cost", "lower band", "upper band"],
            _forecast_rows(context["forecast"]),
        ),
        "",
        "Regenerate with `make report` after `make build`.",
        "",
    ]
    return "\n".join(lines)


def _html(context: dict[str, object]) -> str:
    detection = context["detection"]
    assert isinstance(detection, tuple)
    month_label = f"{context['billing_month']:%Y-%m}"
    start = html.escape(str(context["start_date"]))
    end = html.escape(str(context["end_date"]))
    parts = [
        "<!DOCTYPE html>",
        '<html lang="en">',
        "<head>",
        '<meta charset="utf-8">',
        "<title>Synthetic cloud cost summary</title>",
        "<style>",
        "body { font-family: Georgia, serif; max-width: 960px; margin: 2rem auto;",
        "  padding: 0 1rem; color: #1c1c1c; }",
        "table { border-collapse: collapse; width: 100%; margin: 0.5rem 0 1.5rem; }",
        "th, td { border-bottom: 1px solid #ccc; text-align: left; padding: 0.35rem 0.5rem;",
        "  font-family: ui-sans-serif, sans-serif; font-size: 0.92rem; }",
        "th { background: #f4f1ea; }",
        ".banner { background: #f4f1ea; border-left: 4px solid #8a5a00;",
        "  padding: 0.75rem 1rem; }",
        "</style>",
        "</head>",
        "<body>",
        "<h1>Synthetic cloud cost summary</h1>",
        '<p class="banner">Synthetic data (synthetic-finops-portfolio).',
        "These figures are computed from the generated extract.",
        "They are not real cloud spend.</p>",
        "<h2>Window</h2>",
        "<ul>",
        f"<li>Usage dates: {start} through {end}</li>",
        f"<li>Daily fact rows: {context['fact_rows']:,}</li>",
        f"<li>Gross cost: {html.escape(_money(context['gross_cost']))}</li>",
        f"<li>Credits (positive magnitude): {html.escape(_money(context['credit_amount']))}</li>",
        f"<li>Net cost: {html.escape(_money(context['net_cost']))}</li>",
        "</ul>",
        _html_table(
            ["extract", "rows"],
            [[row.extract_name, f"{int(row.rows):,}"] for row in _rows(context["row_counts"])],
        ),
        "<h2>Net cost by cloud</h2>",
        _html_table(
            ["cloud", "net cost", "gross cost"],
            [
                [row.cloud_provider, _money(row.net_cost), _money(row.gross_cost)]
                for row in _rows(context["by_cloud"])
            ],
        ),
        f"<h2>Latest month ({html.escape(month_label)})</h2>",
        "<h3>By team</h3>",
        _html_table(
            ["team", "net cost"],
            [[row.team, _money(row.net_cost)] for row in _rows(context["by_team"])],
        ),
        "<h3>Largest services</h3>",
        _html_table(
            ["cloud", "service", "net cost"],
            [
                [row.cloud_provider, row.service_name, _money(row.net_cost)]
                for row in _rows(context["top_services"])
            ],
        ),
        "<h3>Largest month-over-month moves</h3>",
        _html_table(
            ["cloud", "service", "this month", "prior month", "change"],
            [_mover_row(row) for row in _rows(context["movers"])],
        ),
        "<h2>Anomaly screen</h2>",
        "<p>Rolling 28-day z-score of daily net cost by account and service.",
        "A day is flagged when at least 14 prior days exist, z &gt;= 3,",
        "and net cost is at least 25% above the trailing mean.</p>",
        "<ul>",
        f"<li>Labelled spike account-service-days: {int(detection[0])}</li>",
        f"<li>Of those, flagged by the screen: {int(detection[1])}</li>",
        f"<li>Flagged days in total: {int(detection[2])}</li>",
        f"<li>Flagged days with no injected spike label: {int(detection[3])}</li>",
        "</ul>",
        _html_table(
            ["date", "cloud", "account", "service", "net cost", "baseline", "z", "spike"],
            [_anomaly_row(row) for row in _rows(context["anomalies"])],
        ),
        "<h2>Unit cost</h2>",
        "<p>Spikes in this dataset scale usage and price together, so unit cost",
        "stays near the anchor rate. Credits lower the net unit cost.</p>",
        _html_table(
            ["service", "usage type", "unit", "gross unit cost", "net unit cost"],
            [
                [
                    row.service_name,
                    row.usage_type,
                    row.usage_unit,
                    f"{float(row.gross_unit_cost):.6f}",
                    f"{float(row.net_unit_cost):.6f}",
                ]
                for row in _rows(context["unit_costs"])
            ],
        ),
        "<h2>Forecast</h2>",
        "<p>OLS trend plus an additive weekday residual. The band is illustrative,",
        "not a calibrated prediction interval. Holdout MAPE is a backtest",
        "on this synthetic series only.</p>",
        _html_table(
            ["series", "holdout MAPE", "MAPE excluding spike days", "slope per day"],
            [_metric_row(item) for item in _meta_series(context)],
        ),
        _html_table(
            ["series", "date", "forecast net cost", "lower band", "upper band"],
            _forecast_rows(context["forecast"]),
        ),
        "</body>",
        "</html>",
        "",
    ]
    return "\n".join(parts)


def _frame(
    connection: duckdb.DuckDBPyConnection,
    query: str,
    params: list[object] | None = None,
) -> pd.DataFrame:
    if params is None:
        return connection.execute(query).df()
    return connection.execute(query, params).df()


def _rows(frame: object) -> list[object]:
    assert isinstance(frame, pd.DataFrame)
    return list(frame.itertuples(index=False))


def _meta_series(context: dict[str, object]) -> list[dict[str, object]]:
    meta = context["meta"]
    assert isinstance(meta, dict)
    series = meta["series"]
    assert isinstance(series, list)
    return series


def _mover_row(row: object) -> list[str]:
    current = float(row.net_cost)  # type: ignore[attr-defined]
    prior = row.prev_month_net_cost  # type: ignore[attr-defined]
    if prior is None or pd.isna(prior) or float(prior) == 0:
        change = "n/a"
        prior_text = "n/a"
    else:
        prior_value = float(prior)
        change = _pct((current - prior_value) / prior_value)
        prior_text = _money(prior_value)
    return [
        row.cloud_provider,  # type: ignore[attr-defined]
        row.service_name,  # type: ignore[attr-defined]
        _money(current),
        prior_text,
        change,
    ]


def _anomaly_row(row: object) -> list[str]:
    spike = row.labelled_spike_id  # type: ignore[attr-defined]
    spike_text = (
        "" if spike is None or (isinstance(spike, float) and pd.isna(spike)) else str(spike)
    )
    return [
        str(_as_date(row.usage_date)),  # type: ignore[attr-defined]
        row.cloud_provider,  # type: ignore[attr-defined]
        row.account_name,  # type: ignore[attr-defined]
        row.service_name,  # type: ignore[attr-defined]
        _money(row.net_cost),  # type: ignore[attr-defined]
        _money(row.rolling_mean_cost),  # type: ignore[attr-defined]
        f"{float(row.z_score):.2f}",  # type: ignore[attr-defined]
        spike_text,
    ]


def _metric_row(item: dict[str, object]) -> list[str]:
    return [
        str(item["series"]),
        _pct(item["holdout_mape"]),
        _pct(item["holdout_mape_excluding_spikes"]),
        f"{float(item['trend_slope_per_day']):.2f}",
    ]


def _forecast_rows(frame: object) -> list[list[str]]:
    assert isinstance(frame, pd.DataFrame)
    rows: list[list[str]] = []
    for series, group in frame.groupby("series", sort=True):
        for record in group.head(7).itertuples(index=False):
            rows.append(
                [
                    str(series),
                    str(record.usage_date),
                    _money(record.forecast_net_cost),
                    _money(record.lower_band),
                    _money(record.upper_band),
                ]
            )
    return rows


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "| " + " | ".join(headers) + " |"
    rule = "| " + " | ".join("---" for _ in headers) + " |"
    body = ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join([head, rule, *body])


def _html_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{html.escape(header)}</th>" for header in headers)
    body = []
    for row in rows:
        cells = "".join(f"<td>{html.escape(str(cell))}</td>" for cell in row)
        body.append(f"<tr>{cells}</tr>")
    return "<table><thead><tr>" + head + "</tr></thead><tbody>" + "".join(body) + "</tbody></table>"


def _money(value: object) -> str:
    return f"${float(value):,.2f}"


def _pct(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "n/a"
    return f"{float(value) * 100:.1f}%"


def _as_date(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    return pd.Timestamp(value).date()


if __name__ == "__main__":
    main()
