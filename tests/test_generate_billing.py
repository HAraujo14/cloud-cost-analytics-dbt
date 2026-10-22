"""Tests for the synthetic billing generator."""

from datetime import date

import pandas as pd
from scripts.catalog import DATASET_LABEL, SPIKES, validate_catalog
from scripts.generate_billing import AWS_COLUMNS, GCP_COLUMNS, generate_extracts


def test_catalog_is_internally_consistent() -> None:
    validate_catalog()


def test_generation_is_deterministic() -> None:
    first = generate_extracts()
    second = generate_extracts()
    pd.testing.assert_frame_equal(first.aws, second.aws)
    pd.testing.assert_frame_equal(first.gcp, second.gcp)


def test_extracts_cover_six_months_and_required_columns() -> None:
    extracts = generate_extracts()
    assert list(extracts.aws.columns) == AWS_COLUMNS
    assert list(extracts.gcp.columns) == GCP_COLUMNS
    aws_dates = pd.to_datetime(extracts.aws["line_item_usage_start_date"]).dt.date
    gcp_dates = pd.to_datetime(extracts.gcp["usage_start_time"]).dt.date
    assert aws_dates.min() == date(2026, 4, 1)
    assert aws_dates.max() == date(2026, 9, 30)
    assert gcp_dates.min() == date(2026, 4, 1)
    assert gcp_dates.max() == date(2026, 9, 30)
    assert aws_dates.nunique() == 183
    assert gcp_dates.nunique() == 183
    assert len(extracts.aws) > 5_000
    assert len(extracts.gcp) > 2_000


def test_every_row_is_labelled_synthetic() -> None:
    extracts = generate_extracts()
    assert set(extracts.aws["_dataset_label"]) == {DATASET_LABEL}
    assert set(extracts.gcp["_dataset_label"]) == {DATASET_LABEL}
    assert extracts.aws["_synthetic"].all()
    assert extracts.gcp["_synthetic"].all()
    assert extracts.aws["line_item_line_item_description"].str.startswith("SYNTHETIC").all()


def test_usage_cost_is_non_negative_and_credits_have_the_export_sign() -> None:
    extracts = generate_extracts()
    aws_usage = extracts.aws[extracts.aws["line_item_line_item_type"] == "Usage"]
    aws_credit = extracts.aws[extracts.aws["line_item_line_item_type"] == "Credit"]
    assert not aws_usage.empty
    assert not aws_credit.empty
    assert (aws_usage["line_item_unblended_cost"] >= 0).all()
    assert (aws_usage["line_item_usage_amount"] >= 0).all()
    assert (aws_credit["line_item_unblended_cost"] < 0).all()
    assert (aws_credit["line_item_usage_amount"] == 0).all()
    assert (extracts.gcp["cost"] >= 0).all()
    assert (extracts.gcp["credits_amount"] <= 0).all()
    assert (extracts.gcp["usage_amount"] >= 0).all()


def test_several_accounts_services_and_tags_are_present() -> None:
    extracts = generate_extracts()
    assert extracts.aws["line_item_usage_account_id"].nunique() >= 4
    assert extracts.gcp["project_id"].nunique() >= 4
    assert extracts.aws["product_servicename"].nunique() >= 6
    assert extracts.gcp["service_description"].nunique() >= 5
    assert set(extracts.aws["resource_tags_user_environment"]) >= {"prod", "staging", "sandbox"}
    assert "data-platform" in set(extracts.aws["resource_tags_user_team"])
    assert "finops" in set(extracts.gcp["label_team"])


def test_injected_spikes_are_present_and_larger_than_the_neighboring_week() -> None:
    extracts = generate_extracts()
    present = set(extracts.aws["_spike_id"].dropna()) | set(extracts.gcp["_spike_id"].dropna())
    assert present == {spike.spike_id for spike in SPIKES}

    aws = extracts.aws[extracts.aws["line_item_line_item_type"] == "Usage"].copy()
    aws["usage_date"] = pd.to_datetime(aws["line_item_usage_start_date"]).dt.date
    ec2 = aws[
        (aws["line_item_usage_account_id"] == "100000000001")
        & (aws["product_servicename"] == "Amazon Elastic Compute Cloud")
    ]
    daily = ec2.groupby("usage_date")["line_item_unblended_cost"].sum()
    spike = daily.loc[[date(2026, 6, 9), date(2026, 6, 10), date(2026, 6, 11)]].mean()
    baseline = daily.loc[[date(2026, 6, 2), date(2026, 6, 3), date(2026, 6, 4)]].mean()
    assert spike > baseline * 3

    gcp = extracts.gcp.copy()
    gcp["usage_date"] = pd.to_datetime(gcp["usage_start_time"]).dt.date
    analysis = gcp[
        (gcp["project_id"] == "synth-gcp-prod-analytics")
        & (gcp["service_description"] == "BigQuery")
        & (gcp["sku_description"] == "Analysis")
        & (gcp["label_application"] == "warehouse")
    ]
    bq_daily = analysis.groupby("usage_date")["cost"].sum()
    assert bq_daily.loc[date(2026, 7, 21)] > bq_daily.loc[date(2026, 7, 14)] * 5
