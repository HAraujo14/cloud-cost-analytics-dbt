"""Tests for the local cost forecast."""

from datetime import date, timedelta

import pandas as pd
from scripts.forecast_cost import forecast_daily_series


def _history(start: date, days: int, weekday_cost: float, weekend_cost: float, slope: float = 0.0):
    dates = [start + timedelta(days=offset) for offset in range(days)]
    values = []
    for offset, day in enumerate(dates):
        base = weekday_cost if day.weekday() < 5 else weekend_cost
        values.append(base + slope * offset)
    return pd.Series(pd.to_datetime(dates)), pd.Series(values)


def test_forecast_horizon_and_non_negative_values() -> None:
    dates, values = _history(date(2026, 4, 1), 90, 100.0, 60.0, slope=0.1)
    result = forecast_daily_series(
        dates,
        values,
        anomaly_dates=set(),
        series="total",
        horizon=14,
    )
    assert len(result.frame) == 14
    assert result.frame["forecast_net_cost"].ge(0).all()
    assert result.frame["lower_band"].ge(0).all()
    assert (result.frame["upper_band"] >= result.frame["forecast_net_cost"]).all()
    assert result.frame["usage_date"].iloc[0] == "2026-06-30"
    assert result.metrics["holdout_mape"] is not None
    assert result.metrics["holdout_mape"] < 0.05


def test_weekend_forecast_is_below_weekday_forecast() -> None:
    dates, values = _history(date(2026, 4, 6), 70, 100.0, 40.0)
    result = forecast_daily_series(
        dates,
        values,
        anomaly_dates=set(),
        series="aws",
        horizon=14,
    )
    frame = result.frame.copy()
    frame["dow"] = pd.to_datetime(frame["usage_date"]).dt.dayofweek
    weekend = frame.loc[frame["dow"] >= 5, "forecast_net_cost"].mean()
    weekday = frame.loc[frame["dow"] < 5, "forecast_net_cost"].mean()
    assert weekend < weekday


def test_forecast_still_runs_when_every_day_is_marked_anomalous() -> None:
    dates, values = _history(date(2026, 4, 1), 40, 80.0, 80.0)
    anomaly_dates = set(pd.to_datetime(dates).dt.date)
    result = forecast_daily_series(
        dates,
        values,
        anomaly_dates=anomaly_dates,
        series="gcp",
        horizon=7,
    )
    assert len(result.frame) == 7
    assert result.frame["forecast_net_cost"].notna().all()
    assert result.metrics["spike_days_excluded_from_fit"] == 0
