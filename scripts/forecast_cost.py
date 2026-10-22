"""Forecast daily net cost with a trend plus weekday residual.

This is a small explanatory model for the portfolio project:

* ordinary least squares of net cost on a day index
* an additive residual for each weekday, estimated on the training days
* an illustrative band of +/- 1.96 residual standard deviations

The band is not a calibrated prediction interval. Injected spike days are left
out of the fit when the anomaly mart marks them, because those days are
labelled incidents rather than the baseline run-rate. A separate backtest
holds out the last 28 days and reports MAPE on this synthetic series only.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date

import duckdb
import numpy as np
import pandas as pd

from scripts.paths import FORECAST_CSV, FORECAST_META, WAREHOUSE_PATH

METHOD = "ols_trend_plus_weekday"
HORIZON_DAYS = 30
HOLDOUT_DAYS = 28
MIN_TRAIN_DAYS = 21


@dataclass(frozen=True)
class SeriesForecast:
    """Future forecast rows and the backtest numbers that accompany them."""

    series: str
    frame: pd.DataFrame
    metrics: dict[str, object]


def forecast_daily_series(
    dates: pd.Series,
    values: pd.Series,
    anomaly_dates: set[date],
    *,
    series: str,
    horizon: int = HORIZON_DAYS,
    holdout_days: int = HOLDOUT_DAYS,
) -> SeriesForecast:
    """Forecast ``horizon`` days past the last observed date."""
    history = (
        pd.DataFrame({"usage_date": pd.to_datetime(dates), "net_cost": values})
        .dropna()
        .sort_values("usage_date")
        .drop_duplicates("usage_date")
        .reset_index(drop=True)
    )
    if history.empty:
        raise ValueError(f"{series} has no history to forecast")

    observed_dates = [value.date() for value in history["usage_date"]]
    anomaly_mask = np.array([day in anomaly_dates for day in observed_dates], dtype=bool)
    n_rows = len(history)
    holdout = min(holdout_days, max(n_rows // 5, 1))
    if n_rows - holdout < MIN_TRAIN_DAYS:
        holdout = max(n_rows - MIN_TRAIN_DAYS, 0)

    backtest_train = np.zeros(n_rows, dtype=bool)
    if holdout < n_rows:
        backtest_train[: n_rows - holdout] = True
    backtest_train = _relax_training_mask(backtest_train, anomaly_mask)
    backtest_fit = _fit(history, backtest_train)

    holdout_actual = history["net_cost"].to_numpy()[n_rows - holdout :] if holdout else np.array([])
    holdout_dates = observed_dates[n_rows - holdout :] if holdout else []
    if holdout:
        holdout_predicted = np.clip(
            _predict(history["usage_date"], backtest_fit)[n_rows - holdout :],
            0,
            None,
        )
    else:
        holdout_predicted = np.array([])
    clean_holdout = np.array([day not in anomaly_dates for day in holdout_dates], dtype=bool)

    forecast_train = _relax_training_mask(np.ones(n_rows, dtype=bool), anomaly_mask)
    forecast_fit = _fit(history, forecast_train)
    future_index = pd.date_range(
        history["usage_date"].max() + pd.Timedelta(days=1),
        periods=horizon,
        freq="D",
    )
    origin = history["usage_date"].min()
    future_x = (future_index - origin).days.to_numpy().astype(float)
    future_dow = future_index.dayofweek.to_numpy()
    point = _apply_fit(forecast_fit, future_x, future_dow)
    point = np.clip(point, 0, None)
    lower = np.clip(point - 1.96 * forecast_fit.residual_stddev, 0, None)
    upper = point + 1.96 * forecast_fit.residual_stddev

    frame = pd.DataFrame(
        {
            "series": series,
            "usage_date": [value.date().isoformat() for value in future_index],
            "forecast_net_cost": np.round(point, 6),
            "lower_band": np.round(lower, 6),
            "upper_band": np.round(upper, 6),
            "method": METHOD,
            "is_synthetic": True,
        }
    )
    metrics: dict[str, object] = {
        "series": series,
        "method": METHOD,
        "horizon_days": horizon,
        "holdout_days": holdout,
        "training_days": int(forecast_train.sum()),
        "spike_days_excluded_from_fit": int((~forecast_train).sum()),
        "trend_slope_per_day": round(forecast_fit.slope, 6),
        "residual_stddev": round(forecast_fit.residual_stddev, 6),
        "holdout_mape": _round_optional(_mape(holdout_actual, holdout_predicted)),
        "holdout_mape_excluding_spikes": _round_optional(
            _mape(holdout_actual[clean_holdout], holdout_predicted[clean_holdout])
            if holdout and clean_holdout.any()
            else None
        ),
        "disclaimer": (
            "Backtest MAPE is computed on this synthetic series only. "
            "The band is +/- 1.96 residual standard deviations and is illustrative, "
            "not a calibrated prediction interval."
        ),
    }
    return SeriesForecast(series=series, frame=frame, metrics=metrics)


def write_forecasts(results: list[SeriesForecast]) -> None:
    """Write the future forecast and the backtest metrics."""
    FORECAST_CSV.parent.mkdir(parents=True, exist_ok=True)
    frame = pd.concat([result.frame for result in results], ignore_index=True)
    frame.to_csv(FORECAST_CSV, index=False, float_format="%.6f")
    payload = {
        "dataset_label": "synthetic-finops-portfolio",
        "method": METHOD,
        "series": [result.metrics for result in results],
    }
    FORECAST_META.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def main() -> None:
    if not WAREHOUSE_PATH.exists():
        raise SystemExit(f"Missing {WAREHOUSE_PATH}. Run `dbt build` before the forecast.")
    connection = duckdb.connect(str(WAREHOUSE_PATH), read_only=True)
    try:
        daily = connection.execute(
            """
            select usage_date, cloud_provider, sum(net_cost) as net_cost
            from marts.fct_daily_cost
            group by 1, 2
            order by 1, 2
            """
        ).df()
        anomalies = connection.execute(
            """
            select distinct usage_date, cloud_provider
            from marts.mart_service_anomalies
            where is_cost_spike
            """
        ).df()
    finally:
        connection.close()

    daily["usage_date"] = pd.to_datetime(daily["usage_date"])
    anomaly_days = {
        (pd.Timestamp(row.usage_date).date(), row.cloud_provider)
        for row in anomalies.itertuples(index=False)
    }
    total_anomaly_days = {day for day, _cloud in anomaly_days}
    total_daily = daily.groupby("usage_date", as_index=False)["net_cost"].sum()

    results = [
        forecast_daily_series(
            total_daily["usage_date"],
            total_daily["net_cost"],
            total_anomaly_days,
            series="total",
        )
    ]
    for cloud in ("aws", "gcp"):
        cloud_daily = daily[daily["cloud_provider"] == cloud]
        cloud_anomalies = {day for day, provider in anomaly_days if provider == cloud}
        results.append(
            forecast_daily_series(
                cloud_daily["usage_date"],
                cloud_daily["net_cost"],
                cloud_anomalies,
                series=cloud,
            )
        )

    write_forecasts(results)
    total = next(result for result in results if result.series == "total")
    print(
        f"Wrote {FORECAST_CSV} horizon={HORIZON_DAYS} "
        f"total_holdout_mape={total.metrics['holdout_mape']}"
    )


@dataclass(frozen=True)
class _Fit:
    origin: pd.Timestamp
    intercept: float
    slope: float
    weekday_factors: np.ndarray
    residual_stddev: float


def _relax_training_mask(train_mask: np.ndarray, anomaly_mask: np.ndarray) -> np.ndarray:
    """Drop labelled spike days unless that would leave too little history."""
    candidate = train_mask & ~anomaly_mask
    if int(candidate.sum()) >= MIN_TRAIN_DAYS:
        return candidate
    return train_mask


def _fit(history: pd.DataFrame, train_mask: np.ndarray) -> _Fit:
    dates = history["usage_date"]
    origin = dates.min()
    x_values = (dates - origin).dt.days.to_numpy().astype(float)
    y_values = history["net_cost"].to_numpy().astype(float)
    day_of_week = dates.dt.dayofweek.to_numpy()
    if int(train_mask.sum()) < 2:
        train_mask = np.ones(len(history), dtype=bool)
    slope, intercept = np.polyfit(x_values[train_mask], y_values[train_mask], 1)
    fitted = intercept + slope * x_values
    trend_residuals = y_values - fitted
    factors = np.zeros(7)
    for weekday in range(7):
        selected = train_mask & (day_of_week == weekday)
        if selected.any():
            factors[weekday] = float(trend_residuals[selected].mean())
    factors = factors - float(factors.mean())
    seasonal_residuals = y_values - (fitted + factors[day_of_week])
    if int(train_mask.sum()) > 2:
        residual_stddev = float(seasonal_residuals[train_mask].std(ddof=1))
    else:
        residual_stddev = 0.0
    if not np.isfinite(residual_stddev):
        residual_stddev = 0.0
    return _Fit(
        origin=origin,
        intercept=float(intercept),
        slope=float(slope),
        weekday_factors=factors,
        residual_stddev=residual_stddev,
    )


def _predict(dates: pd.Series, fit: _Fit) -> np.ndarray:
    x_values = (dates - fit.origin).dt.days.to_numpy().astype(float)
    day_of_week = dates.dt.dayofweek.to_numpy()
    return _apply_fit(fit, x_values, day_of_week)


def _apply_fit(fit: _Fit, x_values: np.ndarray, day_of_week: np.ndarray) -> np.ndarray:
    return fit.intercept + fit.slope * x_values + fit.weekday_factors[day_of_week]


def _mape(actual: np.ndarray, predicted: np.ndarray) -> float | None:
    if len(actual) == 0:
        return None
    actual = np.asarray(actual, dtype=float)
    predicted = np.asarray(predicted, dtype=float)
    usable = actual > 0
    if not usable.any():
        return None
    return float(np.mean(np.abs(actual[usable] - predicted[usable]) / actual[usable]))


def _round_optional(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 6)


if __name__ == "__main__":
    main()
