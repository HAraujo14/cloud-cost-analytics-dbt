"""Generate a synthetic AWS CUR extract and a flattened GCP billing export.

The files follow the column names of those exports closely enough to practice
staging models. They are daily, not hourly, and every row carries
``_dataset_label = synthetic-finops-portfolio``. Nothing here is real spend.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta

import numpy as np
import pandas as pd

from scripts.catalog import (
    CURRENCY,
    DATASET_LABEL,
    DEFAULT_SEED,
    END_DATE,
    GCP_SERVICE_IDS,
    SERVICE_CATEGORIES,
    SPIKES,
    START_DATE,
    WORKLOADS,
    Workload,
    matching_spikes,
    validate_catalog,
)
from scripts.paths import (
    ACCOUNT_SEED_PATH,
    AWS_CUR_PATH,
    GCP_BILLING_PATH,
    MANIFEST_PATH,
    SEED_PATH,
)

AWS_COLUMNS = [
    "identity_line_item_id",
    "identity_time_interval",
    "bill_billing_entity",
    "bill_bill_type",
    "bill_payer_account_id",
    "bill_billing_period_start_date",
    "bill_billing_period_end_date",
    "line_item_usage_account_id",
    "line_item_line_item_type",
    "line_item_usage_start_date",
    "line_item_usage_end_date",
    "line_item_product_code",
    "line_item_usage_type",
    "line_item_operation",
    "line_item_availability_zone",
    "line_item_resource_id",
    "line_item_usage_amount",
    "line_item_unblended_rate",
    "line_item_unblended_cost",
    "line_item_net_unblended_cost",
    "line_item_currency_code",
    "line_item_line_item_description",
    "product_servicecode",
    "product_servicename",
    "product_region",
    "product_sku",
    "pricing_unit",
    "resource_tags_user_team",
    "resource_tags_user_environment",
    "resource_tags_user_cost_center",
    "resource_tags_user_application",
    "_synthetic",
    "_dataset_label",
    "_spike_id",
]

GCP_COLUMNS = [
    "billing_row_id",
    "billing_account_id",
    "invoice_month",
    "cost_type",
    "service_id",
    "service_description",
    "sku_id",
    "sku_description",
    "usage_start_time",
    "usage_end_time",
    "project_id",
    "project_number",
    "project_name",
    "label_team",
    "label_environment",
    "label_cost_center",
    "label_application",
    "location_location",
    "location_country",
    "location_region",
    "cost",
    "currency",
    "currency_conversion_rate",
    "usage_amount",
    "usage_unit",
    "usage_amount_in_pricing_units",
    "usage_pricing_unit",
    "credits_name",
    "credits_type",
    "credits_amount",
    "cost_at_list",
    "export_time",
    "_synthetic",
    "_dataset_label",
    "_spike_id",
]


@dataclass(frozen=True)
class BillingExtracts:
    """In-memory synthetic extracts plus the manifest written next to them."""

    aws: pd.DataFrame
    gcp: pd.DataFrame
    manifest: dict[str, object]


def generate_extracts(
    seed: int = DEFAULT_SEED,
    start: date = START_DATE,
    end: date = END_DATE,
) -> BillingExtracts:
    """Build both extracts. The same seed and dates always return the same frames."""
    validate_catalog()
    if end < start:
        raise ValueError("end date is before start date")

    dates = pd.date_range(start, end, freq="D", tz="UTC")
    rng = np.random.default_rng(seed)
    aws_frames: list[pd.DataFrame] = []
    gcp_frames: list[pd.DataFrame] = []
    for workload in WORKLOADS:
        usage, credit, spike_ids = _daily_series(workload, dates, rng)
        if workload.cloud == "aws":
            aws_frames.append(_aws_frame(workload, dates, usage, credit, spike_ids))
        else:
            gcp_frames.append(_gcp_frame(workload, dates, usage, credit, spike_ids))

    aws = (
        pd.concat(aws_frames, ignore_index=True)
        if aws_frames
        else pd.DataFrame(columns=AWS_COLUMNS)
    )
    gcp = (
        pd.concat(gcp_frames, ignore_index=True)
        if gcp_frames
        else pd.DataFrame(columns=GCP_COLUMNS)
    )
    aws = aws[AWS_COLUMNS]
    gcp = gcp[GCP_COLUMNS]
    manifest = _manifest(seed, start, end, aws, gcp)
    return BillingExtracts(aws=aws, gcp=gcp, manifest=manifest)


def main() -> None:
    extracts = generate_extracts()
    write_extracts(extracts)
    print(
        "Wrote synthetic billing extracts "
        f"aws_rows={len(extracts.aws)} gcp_rows={len(extracts.gcp)} "
        f"label={DATASET_LABEL}"
    )
    print(f"  {AWS_CUR_PATH}")
    print(f"  {GCP_BILLING_PATH}")
    print(f"  {MANIFEST_PATH}")


def _daily_series(
    workload: Workload,
    dates: pd.DatetimeIndex,
    rng: np.random.Generator,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return usage, positive credit magnitude, and spike id for each resource-day.

    Usage has shape (resource_count, n_days). Credit is allocated across resources
    in proportion to that resource's cost so the account-level rate is preserved.
    """
    n_days = len(dates)
    day_of_week = dates.dayofweek.to_numpy()
    weekend = np.where(day_of_week >= 5, workload.weekend_factor, 1.0)
    month_index = ((dates.year - dates[0].year) * 12 + (dates.month - dates[0].month)).to_numpy()
    growth = (1.0 + workload.monthly_growth) ** month_index
    if workload.noise_sigma > 0:
        noise = rng.lognormal(0.0, workload.noise_sigma, size=n_days)
        noise = noise / np.exp(workload.noise_sigma**2 / 2.0)
    else:
        noise = np.ones(n_days)

    spike_multiplier = np.ones(n_days)
    spike_ids = np.empty(n_days, dtype=object)
    for index, timestamp in enumerate(dates):
        matched = matching_spikes(workload, timestamp.date())
        if matched:
            spike_multiplier[index] = float(np.prod([spike.multiplier for spike in matched]))
            spike_ids[index] = "|".join(sorted(spike.spike_id for spike in matched))
        else:
            spike_ids[index] = None

    total_usage = workload.base_daily_usage * weekend * growth * noise * spike_multiplier
    if workload.price_model == "monthly_accrual":
        # Store the fraction of a GB-month accrued that day so unit cost stays
        # near the monthly anchor rate instead of the daily storage level.
        days_in_month = dates.to_series().dt.days_in_month.to_numpy()
        total_usage = total_usage / days_in_month

    resource_count = workload.resource_count
    if resource_count == 1:
        shares = np.ones((1, n_days))
    else:
        raw_shares = rng.uniform(0.85, 1.15, size=(resource_count, n_days))
        shares = raw_shares / raw_shares.sum(axis=0, keepdims=True)
    usage = np.round(total_usage * shares, 6)
    gross = np.round(usage * workload.unit_price, 6)
    credit = (
        np.round(gross * workload.credit_rate, 6) if workload.credit_rate else np.zeros_like(gross)
    )
    return usage, credit, spike_ids


def _aws_frame(
    workload: Workload,
    dates: pd.DatetimeIndex,
    usage: np.ndarray,
    credit: np.ndarray,
    spike_ids: np.ndarray,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for resource_index in range(workload.resource_count):
        resource_id = (
            f"syn-aws-{workload.usage_account_id}-{workload.workload_id}-r{resource_index + 1:02d}"
        )
        for day_index, timestamp in enumerate(dates):
            rows.append(
                _aws_usage_row(
                    workload,
                    timestamp,
                    resource_id,
                    resource_index,
                    float(usage[resource_index, day_index]),
                    float(credit[resource_index, day_index]),
                    spike_ids[day_index],
                )
            )
    if workload.credit_rate > 0:
        daily_credit = credit.sum(axis=0)
        for day_index, timestamp in enumerate(dates):
            amount = float(daily_credit[day_index])
            if amount > 0:
                rows.append(_aws_credit_row(workload, timestamp, amount, spike_ids[day_index]))
    return pd.DataFrame(rows)


def _aws_usage_row(
    workload: Workload,
    timestamp: pd.Timestamp,
    resource_id: str,
    resource_index: int,
    usage_amount: float,
    _credit_amount: float,
    spike_id: str | None,
) -> dict[str, object]:
    # Credit is emitted as its own CUR line. The unused argument keeps the
    # call site aligned with the per-resource credit array.
    del _credit_amount
    start, end, period_start, period_end = _windows(timestamp)
    line_id = (
        f"syn-aws-{workload.workload_id}-r{resource_index + 1:02d}-"
        f"{timestamp.strftime('%Y%m%d')}-usage"
    )
    cost = round(usage_amount * workload.unit_price, 6)
    return {
        "identity_line_item_id": line_id,
        "identity_time_interval": _interval(start, end),
        "bill_billing_entity": "AWS",
        "bill_bill_type": "Anniversary",
        "bill_payer_account_id": workload.billing_account_id,
        "bill_billing_period_start_date": period_start,
        "bill_billing_period_end_date": period_end,
        "line_item_usage_account_id": workload.usage_account_id,
        "line_item_line_item_type": "Usage",
        "line_item_usage_start_date": start,
        "line_item_usage_end_date": end,
        "line_item_product_code": workload.service_code,
        "line_item_usage_type": workload.usage_type,
        "line_item_operation": workload.operation,
        "line_item_availability_zone": _zone(workload),
        "line_item_resource_id": resource_id,
        "line_item_usage_amount": usage_amount,
        "line_item_unblended_rate": workload.unit_price,
        "line_item_unblended_cost": cost,
        "line_item_net_unblended_cost": cost,
        "line_item_currency_code": CURRENCY,
        "line_item_line_item_description": (
            f"SYNTHETIC {workload.service_name} {workload.usage_type} ({workload.application})"
        ),
        "product_servicecode": workload.service_code,
        "product_servicename": workload.service_name,
        "product_region": workload.region,
        "product_sku": f"SYN-{workload.workload_id}",
        "pricing_unit": workload.usage_unit,
        "resource_tags_user_team": workload.team,
        "resource_tags_user_environment": workload.environment,
        "resource_tags_user_cost_center": workload.cost_center,
        "resource_tags_user_application": workload.application,
        "_synthetic": True,
        "_dataset_label": DATASET_LABEL,
        "_spike_id": spike_id,
    }


def _aws_credit_row(
    workload: Workload,
    timestamp: pd.Timestamp,
    credit_amount: float,
    spike_id: str | None,
) -> dict[str, object]:
    start, end, period_start, period_end = _windows(timestamp)
    signed = round(-credit_amount, 6)
    line_id = f"syn-aws-{workload.workload_id}-{timestamp.strftime('%Y%m%d')}-credit"
    return {
        "identity_line_item_id": line_id,
        "identity_time_interval": _interval(start, end),
        "bill_billing_entity": "AWS",
        "bill_bill_type": "Anniversary",
        "bill_payer_account_id": workload.billing_account_id,
        "bill_billing_period_start_date": period_start,
        "bill_billing_period_end_date": period_end,
        "line_item_usage_account_id": workload.usage_account_id,
        "line_item_line_item_type": "Credit",
        "line_item_usage_start_date": start,
        "line_item_usage_end_date": end,
        "line_item_product_code": workload.service_code,
        "line_item_usage_type": workload.usage_type,
        "line_item_operation": workload.operation,
        "line_item_availability_zone": None,
        "line_item_resource_id": None,
        "line_item_usage_amount": 0.0,
        "line_item_unblended_rate": None,
        "line_item_unblended_cost": signed,
        "line_item_net_unblended_cost": signed,
        "line_item_currency_code": CURRENCY,
        "line_item_line_item_description": f"SYNTHETIC credit: {workload.credit_name}",
        "product_servicecode": workload.service_code,
        "product_servicename": workload.service_name,
        "product_region": workload.region,
        "product_sku": f"SYN-{workload.workload_id}",
        "pricing_unit": workload.usage_unit,
        "resource_tags_user_team": workload.team,
        "resource_tags_user_environment": workload.environment,
        "resource_tags_user_cost_center": workload.cost_center,
        "resource_tags_user_application": workload.application,
        "_synthetic": True,
        "_dataset_label": DATASET_LABEL,
        "_spike_id": spike_id,
    }


def _gcp_frame(
    workload: Workload,
    dates: pd.DatetimeIndex,
    usage: np.ndarray,
    credit: np.ndarray,
    spike_ids: np.ndarray,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for resource_index in range(workload.resource_count):
        for day_index, timestamp in enumerate(dates):
            rows.append(
                _gcp_row(
                    workload,
                    timestamp,
                    resource_index,
                    float(usage[resource_index, day_index]),
                    float(credit[resource_index, day_index]),
                    spike_ids[day_index],
                )
            )
    return pd.DataFrame(rows)


def _gcp_row(
    workload: Workload,
    timestamp: pd.Timestamp,
    resource_index: int,
    usage_amount: float,
    credit_amount: float,
    spike_id: str | None,
) -> dict[str, object]:
    start, end, _period_start, _period_end = _windows(timestamp)
    cost = round(usage_amount * workload.unit_price, 6)
    signed_credit = round(-credit_amount, 6) if credit_amount else 0.0
    has_credit = signed_credit < 0
    return {
        "billing_row_id": (
            f"syn-gcp-{workload.workload_id}-r{resource_index + 1:02d}-"
            f"{timestamp.strftime('%Y%m%d')}"
        ),
        "billing_account_id": workload.billing_account_id,
        "invoice_month": timestamp.strftime("%Y%m"),
        "cost_type": "regular",
        "service_id": GCP_SERVICE_IDS[workload.service_name],
        "service_description": workload.service_name,
        "sku_id": f"SYN-{workload.workload_id}",
        "sku_description": workload.usage_type,
        "usage_start_time": start,
        "usage_end_time": end,
        "project_id": workload.usage_account_id,
        "project_number": workload.account_number,
        "project_name": workload.account_name,
        "label_team": workload.team,
        "label_environment": workload.environment,
        "label_cost_center": workload.cost_center,
        "label_application": workload.application,
        "location_location": workload.region,
        "location_country": _country(workload.region),
        "location_region": workload.region,
        "cost": cost,
        "currency": CURRENCY,
        "currency_conversion_rate": 1.0,
        "usage_amount": usage_amount,
        "usage_unit": workload.usage_unit,
        "usage_amount_in_pricing_units": usage_amount,
        "usage_pricing_unit": workload.usage_unit,
        "credits_name": workload.credit_name if has_credit else None,
        "credits_type": "COMMITTED_USAGE_DISCOUNT" if has_credit else None,
        "credits_amount": signed_credit,
        "cost_at_list": cost,
        "export_time": end + pd.Timedelta(days=1),
        "_synthetic": True,
        "_dataset_label": DATASET_LABEL,
        "_spike_id": spike_id,
    }


def _windows(
    timestamp: pd.Timestamp,
) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, pd.Timestamp]:
    start = timestamp
    end = timestamp + pd.Timedelta(days=1)
    period_start = timestamp.replace(day=1)
    if period_start.month == 12:
        period_end = period_start.replace(year=period_start.year + 1, month=1)
    else:
        period_end = period_start.replace(month=period_start.month + 1)
    return start, end, period_start, period_end


def _interval(start: pd.Timestamp, end: pd.Timestamp) -> str:
    return f"{start.strftime('%Y-%m-%dT%H:%M:%SZ')}/{end.strftime('%Y-%m-%dT%H:%M:%SZ')}"


def _zone(workload: Workload) -> str | None:
    if workload.zone_level:
        return f"{workload.region}a"
    return None


def _country(region: str) -> str:
    if region.startswith("europe-"):
        return "BE" if region == "europe-west1" else "EU"
    return "US"


def _write_account_seed() -> None:
    rows = []
    seen: set[str] = set()
    for workload in WORKLOADS:
        if workload.usage_account_id in seen:
            continue
        seen.add(workload.usage_account_id)
        rows.append(
            {
                "cloud_provider": workload.cloud,
                "account_id": workload.usage_account_id,
                "account_name": workload.account_name,
                "environment": workload.environment,
                "billing_account_id": workload.billing_account_id,
            }
        )
    pd.DataFrame(rows).sort_values(["cloud_provider", "account_id"]).to_csv(
        ACCOUNT_SEED_PATH,
        index=False,
    )


def _write_service_seed() -> None:
    rows = [
        {
            "cloud_provider": cloud,
            "service_name": service_name,
            "service_category": category,
        }
        for (cloud, service_name), category in sorted(SERVICE_CATEGORIES.items())
    ]
    pd.DataFrame(rows).to_csv(SEED_PATH, index=False)


def _manifest(
    seed: int,
    start: date,
    end: date,
    aws: pd.DataFrame,
    gcp: pd.DataFrame,
) -> dict[str, object]:
    return {
        "dataset_label": DATASET_LABEL,
        "disclaimer": (
            "Synthetic billing data for a personal portfolio project. "
            "Not real cloud spend, not a bill, and not safe to treat as one."
        ),
        "generator": "scripts.generate_billing",
        "seed": seed,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "currency": CURRENCY,
        "grain": "One row per resource per day. AWS credits are separate line items.",
        "aws_rows": int(len(aws)),
        "gcp_rows": int(len(gcp)),
        "aws_unblended_cost": round(float(aws["line_item_unblended_cost"].sum()), 6),
        "gcp_cost": round(float(gcp["cost"].sum()), 6),
        "gcp_credits": round(float(gcp["credits_amount"].sum()), 6),
        "spikes": [
            {
                "spike_id": spike.spike_id,
                "reason": spike.reason,
                "cloud": spike.cloud,
                "start": spike.start.isoformat(),
                "end": spike.end.isoformat(),
                "multiplier": spike.multiplier,
                "usage_account_id": spike.usage_account_id,
                "service_name": spike.service_name,
                "usage_type": spike.usage_type,
                "application": spike.application,
            }
            for spike in SPIKES
        ],
        "workload_count": len(WORKLOADS),
        "price_note": (
            "unit_price values are rounded public list-price anchors for shaping "
            "this synthetic set. They are not current quotes."
        ),
        "generated_schema_version": 1,
        "catalog_snapshot": [asdict(workload) for workload in WORKLOADS],
    }


def _json_default(value: object) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, timedelta):
        return str(value)
    raise TypeError(f"Cannot serialize {type(value)!r}")


def dumps_manifest(manifest: dict[str, object]) -> str:
    """Serialize a manifest, including date fields inside the catalog snapshot."""
    return json.dumps(manifest, indent=2, sort_keys=True, default=_json_default) + "\n"


def write_extracts(extracts: BillingExtracts) -> None:
    """Write parquet extracts, the generation manifest, and the service-category seed."""
    AWS_CUR_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    extracts.aws.to_parquet(AWS_CUR_PATH, index=False)
    extracts.gcp.to_parquet(GCP_BILLING_PATH, index=False)
    MANIFEST_PATH.write_text(dumps_manifest(extracts.manifest))
    _write_service_seed()
    _write_account_seed()


if __name__ == "__main__":
    main()
