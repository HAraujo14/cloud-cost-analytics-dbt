"""Synthetic workload catalog.

Prices are rounded public list-price anchors used only to shape the dataset.
They are not a pricing feed, a quote, or a statement of what any account pays.
Every generated row is labelled synthetic.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

DATASET_LABEL = "synthetic-finops-portfolio"
DEFAULT_SEED = 42
START_DATE = date(2026, 4, 1)
END_DATE = date(2026, 9, 30)
CURRENCY = "USD"

AWS_PAYER_ACCOUNT_ID = "100000000000"
AWS_PROD_PLATFORM = "100000000001"
AWS_PROD_DATA = "100000000002"
AWS_STAGING = "100000000003"
AWS_SANDBOX = "100000000004"

GCP_BILLING_ACCOUNT_ID = "AAAAAA-SYNTH-000001"
GCP_PROD_ANALYTICS = "synth-gcp-prod-analytics"
GCP_PROD_APP = "synth-gcp-prod-app"
GCP_STAGING = "synth-gcp-staging"
GCP_SANDBOX = "synth-gcp-sandbox"

GCP_PROJECT_NUMBERS = {
    GCP_PROD_ANALYTICS: "900000000001",
    GCP_PROD_APP: "900000000002",
    GCP_STAGING: "900000000003",
    GCP_SANDBOX: "900000000004",
}

# Placeholders. Real Cloud Billing service.id values are catalog ids; these
# are prefixed so a row cannot be mistaken for a live export.
GCP_SERVICE_IDS = {
    "Compute Engine": "SYN-COMPUTE-ENGINE",
    "Cloud Storage": "SYN-CLOUD-STORAGE",
    "BigQuery": "SYN-BIGQUERY",
    "Cloud SQL": "SYN-CLOUD-SQL",
    "Kubernetes Engine": "SYN-KUBERNETES-ENGINE",
    "Cloud Logging": "SYN-CLOUD-LOGGING",
    "Networking": "SYN-NETWORKING",
}

ENVIRONMENTS = ("prod", "staging", "sandbox")
TEAMS = (
    "data-platform",
    "product-backend",
    "ml-platform",
    "shared-services",
    "finops",
)

SERVICE_CATEGORIES: dict[tuple[str, str], str] = {
    ("aws", "Amazon Elastic Compute Cloud"): "compute",
    ("aws", "Amazon Simple Storage Service"): "storage",
    ("aws", "Amazon Relational Database Service"): "database",
    ("aws", "AWS Lambda"): "serverless",
    ("aws", "Amazon Elastic Kubernetes Service"): "compute",
    ("aws", "Amazon Virtual Private Cloud"): "network",
    ("aws", "Amazon CloudWatch"): "observability",
    ("aws", "AWS Data Transfer"): "network",
    ("gcp", "Compute Engine"): "compute",
    ("gcp", "Cloud Storage"): "storage",
    ("gcp", "BigQuery"): "analytics",
    ("gcp", "Cloud SQL"): "database",
    ("gcp", "Kubernetes Engine"): "compute",
    ("gcp", "Cloud Logging"): "observability",
    ("gcp", "Networking"): "network",
}


@dataclass(frozen=True)
class Workload:
    """One priced usage stream, before daily noise and resource fan-out."""

    workload_id: str
    cloud: str
    billing_account_id: str
    usage_account_id: str
    account_name: str
    environment: str
    team: str
    cost_center: str
    application: str
    service_code: str
    service_name: str
    usage_type: str
    operation: str
    region: str
    usage_unit: str
    base_daily_usage: float
    unit_price: float
    price_model: str = "unit"
    weekend_factor: float = 1.0
    monthly_growth: float = 0.0
    noise_sigma: float = 0.04
    resource_count: int = 1
    credit_rate: float = 0.0
    credit_name: str = ""
    zone_level: bool = False
    account_number: str | None = None


@dataclass(frozen=True)
class Spike:
    """A labelled cost incident multiplied onto matching workload-days."""

    spike_id: str
    reason: str
    cloud: str
    start: date
    end: date
    multiplier: float
    usage_account_id: str | None = None
    service_name: str | None = None
    usage_type: str | None = None
    application: str | None = None


def _aws(
    workload_id: str,
    account_id: str,
    account_name: str,
    environment: str,
    team: str,
    cost_center: str,
    application: str,
    **kwargs: object,
) -> Workload:
    return Workload(
        workload_id=workload_id,
        cloud="aws",
        billing_account_id=AWS_PAYER_ACCOUNT_ID,
        usage_account_id=account_id,
        account_name=account_name,
        environment=environment,
        team=team,
        cost_center=cost_center,
        application=application,
        **kwargs,  # type: ignore[arg-type]
    )


def _gcp(
    workload_id: str,
    project_id: str,
    account_name: str,
    environment: str,
    team: str,
    cost_center: str,
    application: str,
    **kwargs: object,
) -> Workload:
    return Workload(
        workload_id=workload_id,
        cloud="gcp",
        billing_account_id=GCP_BILLING_ACCOUNT_ID,
        usage_account_id=project_id,
        account_name=account_name,
        environment=environment,
        team=team,
        cost_center=cost_center,
        application=application,
        account_number=GCP_PROJECT_NUMBERS[project_id],
        **kwargs,  # type: ignore[arg-type]
    )


def _workloads() -> tuple[Workload, ...]:
    """Return the catalog in a fixed order. Order is part of the RNG stream."""
    platform = dict(
        account_id=AWS_PROD_PLATFORM,
        account_name="aws-prod-platform",
        environment="prod",
    )
    data = dict(
        account_id=AWS_PROD_DATA,
        account_name="aws-prod-data",
        environment="prod",
    )
    staging = dict(
        account_id=AWS_STAGING,
        account_name="aws-staging",
        environment="staging",
    )
    sandbox = dict(
        account_id=AWS_SANDBOX,
        account_name="aws-sandbox",
        environment="sandbox",
    )
    return (
        _aws(
            "aws-prod-payments-ec2-xl",
            team="product-backend",
            cost_center="CC-200",
            application="payments-api",
            service_code="AmazonEC2",
            service_name="Amazon Elastic Compute Cloud",
            usage_type="BoxUsage:m6i.xlarge",
            operation="RunInstances",
            region="us-east-1",
            usage_unit="hours",
            base_daily_usage=480,
            unit_price=0.192,
            weekend_factor=0.82,
            monthly_growth=0.015,
            noise_sigma=0.04,
            resource_count=6,
            credit_rate=0.12,
            credit_name="Synthetic Savings Plan",
            zone_level=True,
            **platform,
        ),
        _aws(
            "aws-prod-payments-ec2-large",
            team="product-backend",
            cost_center="CC-200",
            application="payments-api",
            service_code="AmazonEC2",
            service_name="Amazon Elastic Compute Cloud",
            usage_type="BoxUsage:m6i.large",
            operation="RunInstances",
            region="us-east-1",
            usage_unit="hours",
            base_daily_usage=192,
            unit_price=0.096,
            weekend_factor=0.82,
            monthly_growth=0.015,
            noise_sigma=0.04,
            resource_count=4,
            credit_rate=0.12,
            credit_name="Synthetic Savings Plan",
            zone_level=True,
            **platform,
        ),
        _aws(
            "aws-prod-web-ec2-large",
            team="product-backend",
            cost_center="CC-200",
            application="web-app",
            service_code="AmazonEC2",
            service_name="Amazon Elastic Compute Cloud",
            usage_type="USE2-BoxUsage:m6i.large",
            operation="RunInstances",
            region="us-west-2",
            usage_unit="hours",
            base_daily_usage=288,
            unit_price=0.096,
            weekend_factor=0.8,
            monthly_growth=0.012,
            noise_sigma=0.045,
            resource_count=4,
            credit_rate=0.12,
            credit_name="Synthetic Savings Plan",
            zone_level=True,
            **platform,
        ),
        _aws(
            "aws-prod-eks",
            team="shared-services",
            cost_center="CC-440",
            application="observability",
            service_code="AmazonEKS",
            service_name="Amazon Elastic Kubernetes Service",
            usage_type="USE1-AmazonEKS-Hours:perCluster",
            operation="CreateCluster",
            region="us-east-1",
            usage_unit="hours",
            base_daily_usage=48,
            unit_price=0.10,
            weekend_factor=1.0,
            monthly_growth=0.0,
            noise_sigma=0.01,
            resource_count=2,
            zone_level=True,
            **platform,
        ),
        _aws(
            "aws-prod-cloudwatch",
            team="shared-services",
            cost_center="CC-440",
            application="observability",
            service_code="AmazonCloudWatch",
            service_name="Amazon CloudWatch",
            usage_type="USE1-VendedLog-Bytes",
            operation="PutLogEvents",
            region="us-east-1",
            usage_unit="GB",
            base_daily_usage=60,
            unit_price=0.50,
            weekend_factor=0.9,
            monthly_growth=0.02,
            noise_sigma=0.05,
            **platform,
        ),
        _aws(
            "aws-prod-nat-hours",
            team="shared-services",
            cost_center="CC-440",
            application="shared-network",
            service_code="AmazonVPC",
            service_name="Amazon Virtual Private Cloud",
            usage_type="NatGateway-Hours",
            operation="NatGateway",
            region="us-east-1",
            usage_unit="hours",
            base_daily_usage=48,
            unit_price=0.045,
            weekend_factor=1.0,
            noise_sigma=0.01,
            resource_count=2,
            **platform,
        ),
        _aws(
            "aws-prod-nat-bytes",
            team="shared-services",
            cost_center="CC-440",
            application="shared-network",
            service_code="AmazonVPC",
            service_name="Amazon Virtual Private Cloud",
            usage_type="NatGateway-Bytes",
            operation="NatGateway",
            region="us-east-1",
            usage_unit="GB",
            base_daily_usage=420,
            unit_price=0.045,
            weekend_factor=0.75,
            monthly_growth=0.01,
            noise_sigma=0.06,
            **platform,
        ),
        _aws(
            "aws-prod-data-transfer",
            team="shared-services",
            cost_center="CC-440",
            application="shared-network",
            service_code="AWSDataTransfer",
            service_name="AWS Data Transfer",
            usage_type="DataTransfer-Out-Bytes",
            operation="PublicDataTransfer",
            region="us-east-1",
            usage_unit="GB",
            base_daily_usage=160,
            unit_price=0.09,
            weekend_factor=0.7,
            monthly_growth=0.01,
            noise_sigma=0.06,
            **platform,
        ),
        _aws(
            "aws-data-s3-storage",
            team="data-platform",
            cost_center="CC-100",
            application="warehouse",
            service_code="AmazonS3",
            service_name="Amazon Simple Storage Service",
            usage_type="TimedStorage-ByteHrs",
            operation="StandardStorage",
            region="us-east-1",
            usage_unit="GB-Month",
            base_daily_usage=150_000,
            unit_price=0.023,
            price_model="monthly_accrual",
            weekend_factor=1.0,
            monthly_growth=0.03,
            noise_sigma=0.005,
            **data,
        ),
        _aws(
            "aws-data-s3-requests",
            team="data-platform",
            cost_center="CC-100",
            application="warehouse",
            service_code="AmazonS3",
            service_name="Amazon Simple Storage Service",
            usage_type="Requests-Tier1",
            operation="GetObject",
            region="us-east-1",
            usage_unit="Requests",
            base_daily_usage=8_000_000,
            unit_price=0.0000004,
            weekend_factor=0.6,
            monthly_growth=0.01,
            noise_sigma=0.08,
            **data,
        ),
        _aws(
            "aws-data-rds-hours",
            team="data-platform",
            cost_center="CC-100",
            application="warehouse",
            service_code="AmazonRDS",
            service_name="Amazon Relational Database Service",
            usage_type="InstanceUsage:db.r6g.xlarge",
            operation="CreateDBInstance",
            region="us-east-1",
            usage_unit="hours",
            base_daily_usage=48,
            unit_price=0.52,
            weekend_factor=1.0,
            noise_sigma=0.01,
            resource_count=2,
            zone_level=True,
            **data,
        ),
        _aws(
            "aws-data-rds-storage",
            team="data-platform",
            cost_center="CC-100",
            application="warehouse",
            service_code="AmazonRDS",
            service_name="Amazon Relational Database Service",
            usage_type="GP3-Storage",
            operation="CreateDBInstance",
            region="us-east-1",
            usage_unit="GB-Month",
            base_daily_usage=6_000,
            unit_price=0.115,
            price_model="monthly_accrual",
            weekend_factor=1.0,
            monthly_growth=0.02,
            noise_sigma=0.005,
            **data,
        ),
        _aws(
            "aws-data-batch-ec2",
            team="data-platform",
            cost_center="CC-100",
            application="batch-etl",
            service_code="AmazonEC2",
            service_name="Amazon Elastic Compute Cloud",
            usage_type="BoxUsage:m6i.2xlarge",
            operation="RunInstances",
            region="us-east-1",
            usage_unit="hours",
            base_daily_usage=144,
            unit_price=0.384,
            weekend_factor=0.25,
            monthly_growth=0.02,
            noise_sigma=0.05,
            resource_count=6,
            credit_rate=0.08,
            credit_name="Synthetic Savings Plan",
            zone_level=True,
            **data,
        ),
        _aws(
            "aws-data-lambda-duration",
            team="data-platform",
            cost_center="CC-100",
            application="batch-etl",
            service_code="AWSLambda",
            service_name="AWS Lambda",
            usage_type="USE1-Lambda-GB-Second",
            operation="Invoke",
            region="us-east-1",
            usage_unit="GB-Seconds",
            base_daily_usage=2_500_000,
            unit_price=0.0000166667,
            weekend_factor=0.3,
            monthly_growth=0.02,
            noise_sigma=0.07,
            **data,
        ),
        _aws(
            "aws-data-lambda-requests",
            team="data-platform",
            cost_center="CC-100",
            application="batch-etl",
            service_code="AWSLambda",
            service_name="AWS Lambda",
            usage_type="Request",
            operation="Invoke",
            region="us-east-1",
            usage_unit="Requests",
            base_daily_usage=15_000_000,
            unit_price=0.0000002,
            weekend_factor=0.3,
            monthly_growth=0.02,
            noise_sigma=0.07,
            **data,
        ),
        _aws(
            "aws-staging-web-ec2",
            team="product-backend",
            cost_center="CC-200",
            application="web-app",
            service_code="AmazonEC2",
            service_name="Amazon Elastic Compute Cloud",
            usage_type="BoxUsage:m6i.large",
            operation="RunInstances",
            region="us-east-1",
            usage_unit="hours",
            base_daily_usage=96,
            unit_price=0.096,
            weekend_factor=0.4,
            monthly_growth=0.005,
            noise_sigma=0.05,
            resource_count=2,
            zone_level=True,
            **staging,
        ),
        _aws(
            "aws-staging-rds",
            team="product-backend",
            cost_center="CC-200",
            application="web-app",
            service_code="AmazonRDS",
            service_name="Amazon Relational Database Service",
            usage_type="InstanceUsage:db.r6g.large",
            operation="CreateDBInstance",
            region="us-east-1",
            usage_unit="hours",
            base_daily_usage=24,
            unit_price=0.26,
            weekend_factor=1.0,
            noise_sigma=0.02,
            zone_level=True,
            **staging,
        ),
        _aws(
            "aws-staging-s3",
            team="data-platform",
            cost_center="CC-100",
            application="warehouse",
            service_code="AmazonS3",
            service_name="Amazon Simple Storage Service",
            usage_type="TimedStorage-ByteHrs",
            operation="StandardStorage",
            region="us-east-1",
            usage_unit="GB-Month",
            base_daily_usage=8_000,
            unit_price=0.023,
            price_model="monthly_accrual",
            weekend_factor=1.0,
            monthly_growth=0.01,
            noise_sigma=0.005,
            **staging,
        ),
        _aws(
            "aws-sandbox-ec2",
            team="finops",
            cost_center="CC-150",
            application="sandbox-experiments",
            service_code="AmazonEC2",
            service_name="Amazon Elastic Compute Cloud",
            usage_type="BoxUsage:m6i.large",
            operation="RunInstances",
            region="us-east-1",
            usage_unit="hours",
            base_daily_usage=24,
            unit_price=0.096,
            weekend_factor=0.5,
            noise_sigma=0.03,
            zone_level=True,
            **sandbox,
        ),
        _gcp(
            "gcp-analytics-bq-analysis",
            GCP_PROD_ANALYTICS,
            "gcp-prod-analytics",
            "prod",
            team="data-platform",
            cost_center="CC-100",
            application="warehouse",
            service_code=GCP_SERVICE_IDS["BigQuery"],
            service_name="BigQuery",
            usage_type="Analysis",
            operation="job.bigquery",
            region="us-central1",
            usage_unit="TiB",
            base_daily_usage=6.5,
            unit_price=6.25,
            weekend_factor=0.28,
            monthly_growth=0.025,
            noise_sigma=0.06,
        ),
        _gcp(
            "gcp-analytics-bq-storage",
            GCP_PROD_ANALYTICS,
            "gcp-prod-analytics",
            "prod",
            team="data-platform",
            cost_center="CC-100",
            application="warehouse",
            service_code=GCP_SERVICE_IDS["BigQuery"],
            service_name="BigQuery",
            usage_type="Active Logical Storage",
            operation="storage.logical",
            region="us-central1",
            usage_unit="GB-Month",
            base_daily_usage=50_000,
            unit_price=0.02,
            price_model="monthly_accrual",
            weekend_factor=1.0,
            monthly_growth=0.035,
            noise_sigma=0.004,
        ),
        _gcp(
            "gcp-analytics-gcs",
            GCP_PROD_ANALYTICS,
            "gcp-prod-analytics",
            "prod",
            team="data-platform",
            cost_center="CC-100",
            application="warehouse",
            service_code=GCP_SERVICE_IDS["Cloud Storage"],
            service_name="Cloud Storage",
            usage_type="Standard Storage",
            operation="storage.standard",
            region="us-central1",
            usage_unit="GB-Month",
            base_daily_usage=90_000,
            unit_price=0.02,
            price_model="monthly_accrual",
            weekend_factor=1.0,
            monthly_growth=0.03,
            noise_sigma=0.004,
        ),
        _gcp(
            "gcp-analytics-gke",
            GCP_PROD_ANALYTICS,
            "gcp-prod-analytics",
            "prod",
            team="data-platform",
            cost_center="CC-100",
            application="batch-etl",
            service_code=GCP_SERVICE_IDS["Kubernetes Engine"],
            service_name="Kubernetes Engine",
            usage_type="ClusterManagement",
            operation="cluster.management",
            region="us-central1",
            usage_unit="hours",
            base_daily_usage=24,
            unit_price=0.10,
            weekend_factor=1.0,
            noise_sigma=0.01,
            zone_level=True,
        ),
        _gcp(
            "gcp-analytics-gce",
            GCP_PROD_ANALYTICS,
            "gcp-prod-analytics",
            "prod",
            team="data-platform",
            cost_center="CC-100",
            application="batch-etl",
            service_code=GCP_SERVICE_IDS["Compute Engine"],
            service_name="Compute Engine",
            usage_type="e2-standard-4",
            operation="compute.instances.compute",
            region="us-central1",
            usage_unit="hours",
            base_daily_usage=144,
            unit_price=0.134,
            weekend_factor=0.9,
            monthly_growth=0.01,
            noise_sigma=0.03,
            resource_count=6,
            credit_rate=0.18,
            credit_name="Synthetic committed use discount",
            zone_level=True,
        ),
        _gcp(
            "gcp-analytics-logging",
            GCP_PROD_ANALYTICS,
            "gcp-prod-analytics",
            "prod",
            team="shared-services",
            cost_center="CC-440",
            application="observability",
            service_code=GCP_SERVICE_IDS["Cloud Logging"],
            service_name="Cloud Logging",
            usage_type="Log Volume",
            operation="logging.write",
            region="us-central1",
            usage_unit="GiB",
            base_daily_usage=25,
            unit_price=0.50,
            weekend_factor=0.85,
            monthly_growth=0.02,
            noise_sigma=0.05,
        ),
        _gcp(
            "gcp-ml-bq-analysis",
            GCP_PROD_ANALYTICS,
            "gcp-prod-analytics",
            "prod",
            team="ml-platform",
            cost_center="CC-310",
            application="feature-store",
            service_code=GCP_SERVICE_IDS["BigQuery"],
            service_name="BigQuery",
            usage_type="Analysis",
            operation="job.bigquery",
            region="us-central1",
            usage_unit="TiB",
            base_daily_usage=1.4,
            unit_price=6.25,
            weekend_factor=0.4,
            monthly_growth=0.03,
            noise_sigma=0.08,
        ),
        _gcp(
            "gcp-ml-gce",
            GCP_PROD_ANALYTICS,
            "gcp-prod-analytics",
            "prod",
            team="ml-platform",
            cost_center="CC-310",
            application="feature-store",
            service_code=GCP_SERVICE_IDS["Compute Engine"],
            service_name="Compute Engine",
            usage_type="e2-standard-8",
            operation="compute.instances.compute",
            region="us-central1",
            usage_unit="hours",
            base_daily_usage=48,
            unit_price=0.268,
            weekend_factor=0.7,
            monthly_growth=0.02,
            noise_sigma=0.05,
            resource_count=2,
            credit_rate=0.18,
            credit_name="Synthetic committed use discount",
            zone_level=True,
        ),
        _gcp(
            "gcp-app-gce",
            GCP_PROD_APP,
            "gcp-prod-app",
            "prod",
            team="product-backend",
            cost_center="CC-200",
            application="web-app",
            service_code=GCP_SERVICE_IDS["Compute Engine"],
            service_name="Compute Engine",
            usage_type="e2-standard-4",
            operation="compute.instances.compute",
            region="europe-west1",
            usage_unit="hours",
            base_daily_usage=240,
            unit_price=0.134,
            weekend_factor=0.8,
            monthly_growth=0.012,
            noise_sigma=0.04,
            resource_count=5,
            credit_rate=0.15,
            credit_name="Synthetic committed use discount",
            zone_level=True,
        ),
        _gcp(
            "gcp-app-cloudsql",
            GCP_PROD_APP,
            "gcp-prod-app",
            "prod",
            team="product-backend",
            cost_center="CC-200",
            application="web-app",
            service_code=GCP_SERVICE_IDS["Cloud SQL"],
            service_name="Cloud SQL",
            usage_type="db-custom-4-16384",
            operation="cloudsql.instance",
            region="europe-west1",
            usage_unit="hours",
            base_daily_usage=48,
            unit_price=0.32,
            weekend_factor=1.0,
            noise_sigma=0.015,
            resource_count=2,
            zone_level=True,
        ),
        _gcp(
            "gcp-app-egress",
            GCP_PROD_APP,
            "gcp-prod-app",
            "prod",
            team="product-backend",
            cost_center="CC-200",
            application="web-app",
            service_code=GCP_SERVICE_IDS["Networking"],
            service_name="Networking",
            usage_type="Internet egress",
            operation="network.egress",
            region="europe-west1",
            usage_unit="GiB",
            base_daily_usage=260,
            unit_price=0.085,
            weekend_factor=0.72,
            monthly_growth=0.015,
            noise_sigma=0.06,
        ),
        _gcp(
            "gcp-app-gke",
            GCP_PROD_APP,
            "gcp-prod-app",
            "prod",
            team="product-backend",
            cost_center="CC-200",
            application="web-app",
            service_code=GCP_SERVICE_IDS["Kubernetes Engine"],
            service_name="Kubernetes Engine",
            usage_type="ClusterManagement",
            operation="cluster.management",
            region="europe-west1",
            usage_unit="hours",
            base_daily_usage=24,
            unit_price=0.10,
            weekend_factor=1.0,
            noise_sigma=0.01,
            zone_level=True,
        ),
        _gcp(
            "gcp-staging-gce",
            GCP_STAGING,
            "gcp-staging",
            "staging",
            team="product-backend",
            cost_center="CC-200",
            application="web-app",
            service_code=GCP_SERVICE_IDS["Compute Engine"],
            service_name="Compute Engine",
            usage_type="e2-standard-4",
            operation="compute.instances.compute",
            region="us-central1",
            usage_unit="hours",
            base_daily_usage=48,
            unit_price=0.134,
            weekend_factor=0.35,
            noise_sigma=0.05,
            resource_count=2,
            zone_level=True,
        ),
        _gcp(
            "gcp-staging-bq",
            GCP_STAGING,
            "gcp-staging",
            "staging",
            team="data-platform",
            cost_center="CC-100",
            application="warehouse",
            service_code=GCP_SERVICE_IDS["BigQuery"],
            service_name="BigQuery",
            usage_type="Analysis",
            operation="job.bigquery",
            region="us-central1",
            usage_unit="TiB",
            base_daily_usage=0.4,
            unit_price=6.25,
            weekend_factor=0.2,
            noise_sigma=0.1,
        ),
        _gcp(
            "gcp-sandbox-gce",
            GCP_SANDBOX,
            "gcp-sandbox",
            "sandbox",
            team="finops",
            cost_center="CC-150",
            application="sandbox-experiments",
            service_code=GCP_SERVICE_IDS["Compute Engine"],
            service_name="Compute Engine",
            usage_type="e2-standard-2",
            operation="compute.instances.compute",
            region="us-central1",
            usage_unit="hours",
            base_daily_usage=12,
            unit_price=0.067,
            weekend_factor=0.4,
            noise_sigma=0.04,
            zone_level=True,
        ),
        _gcp(
            "gcp-sandbox-bq",
            GCP_SANDBOX,
            "gcp-sandbox",
            "sandbox",
            team="finops",
            cost_center="CC-150",
            application="sandbox-experiments",
            service_code=GCP_SERVICE_IDS["BigQuery"],
            service_name="BigQuery",
            usage_type="Analysis",
            operation="job.bigquery",
            region="us-central1",
            usage_unit="TiB",
            base_daily_usage=0.15,
            unit_price=6.25,
            weekend_factor=0.3,
            noise_sigma=0.1,
        ),
    )


WORKLOADS: tuple[Workload, ...] = _workloads()

SPIKES: tuple[Spike, ...] = (
    Spike(
        spike_id="syn-ec2-autoscale",
        reason="Synthetic incident: payments-api and web-app autoscaling did not scale in.",
        cloud="aws",
        usage_account_id=AWS_PROD_PLATFORM,
        service_name="Amazon Elastic Compute Cloud",
        start=date(2026, 6, 9),
        end=date(2026, 6, 11),
        multiplier=3.8,
    ),
    Spike(
        spike_id="syn-bq-full-scan",
        reason="Synthetic incident: a scheduled query scanned an unpartitioned table.",
        cloud="gcp",
        usage_account_id=GCP_PROD_ANALYTICS,
        service_name="BigQuery",
        usage_type="Analysis",
        application="warehouse",
        start=date(2026, 7, 21),
        end=date(2026, 7, 21),
        multiplier=10.0,
    ),
    Spike(
        spike_id="syn-nat-cross-az",
        reason="Synthetic incident: cross-AZ traffic hairpinned through a NAT gateway.",
        cloud="aws",
        usage_account_id=AWS_PROD_PLATFORM,
        service_name="Amazon Virtual Private Cloud",
        usage_type="NatGateway-Bytes",
        start=date(2026, 8, 18),
        end=date(2026, 8, 19),
        multiplier=6.0,
    ),
    Spike(
        spike_id="syn-sandbox-ec2",
        reason="Synthetic incident: sandbox instances left running at a high replica count.",
        cloud="aws",
        usage_account_id=AWS_SANDBOX,
        service_name="Amazon Elastic Compute Cloud",
        start=date(2026, 5, 12),
        end=date(2026, 5, 12),
        multiplier=15.0,
    ),
)


def validate_catalog() -> None:
    """Fail fast if the catalog contradicts the model grain."""
    ids = [workload.workload_id for workload in WORKLOADS]
    if len(ids) != len(set(ids)):
        raise ValueError("workload_id values must be unique")

    names: dict[str, str] = {}
    environments: dict[str, str] = {}
    for workload in WORKLOADS:
        if workload.cloud not in {"aws", "gcp"}:
            raise ValueError(f"{workload.workload_id} has an unknown cloud")
        if workload.price_model not in {"unit", "monthly_accrual"}:
            raise ValueError(f"{workload.workload_id} has an unknown price model")
        if workload.base_daily_usage < 0 or workload.unit_price < 0:
            raise ValueError(f"{workload.workload_id} has a negative price or usage")
        if not 0 <= workload.credit_rate < 1:
            raise ValueError(f"{workload.workload_id} has an invalid credit rate")
        if workload.environment not in ENVIRONMENTS:
            raise ValueError(f"{workload.workload_id} has an unknown environment")
        if workload.team not in TEAMS:
            raise ValueError(f"{workload.workload_id} has an unknown team")
        if workload.resource_count < 1:
            raise ValueError(f"{workload.workload_id} needs at least one resource")
        key = (workload.cloud, workload.service_name)
        if key not in SERVICE_CATEGORIES:
            raise ValueError(f"missing service category for {key}")
        if workload.cloud == "gcp" and workload.service_name not in GCP_SERVICE_IDS:
            raise ValueError(f"missing GCP service id for {workload.service_name}")
        if workload.cloud == "gcp" and not workload.account_number:
            raise ValueError(f"{workload.workload_id} is missing a project number")
        names.setdefault(workload.usage_account_id, workload.account_name)
        environments.setdefault(workload.usage_account_id, workload.environment)
        if names[workload.usage_account_id] != workload.account_name:
            raise ValueError(f"account {workload.usage_account_id} has two names")
        if environments[workload.usage_account_id] != workload.environment:
            raise ValueError(f"account {workload.usage_account_id} has two environments")

    known_ids = {workload.usage_account_id for workload in WORKLOADS}
    known_services = {workload.service_name for workload in WORKLOADS}
    known_usage_types = {workload.usage_type for workload in WORKLOADS}
    known_apps = {workload.application for workload in WORKLOADS}
    for spike in SPIKES:
        if spike.multiplier < 2:
            raise ValueError(f"{spike.spike_id} is too small to be a labelled spike")
        if spike.start > spike.end:
            raise ValueError(f"{spike.spike_id} has an inverted window")
        if spike.usage_account_id and spike.usage_account_id not in known_ids:
            raise ValueError(f"{spike.spike_id} references an unknown account")
        if spike.service_name and spike.service_name not in known_services:
            raise ValueError(f"{spike.spike_id} references an unknown service")
        if spike.usage_type and spike.usage_type not in known_usage_types:
            raise ValueError(f"{spike.spike_id} references an unknown usage type")
        if spike.application and spike.application not in known_apps:
            raise ValueError(f"{spike.spike_id} references an unknown application")
        if not any(_spike_matches(spike, workload, spike.start) for workload in WORKLOADS):
            raise ValueError(f"{spike.spike_id} matches no workload")


def _spike_matches(spike: Spike, workload: Workload, day: date) -> bool:
    if not spike.start <= day <= spike.end:
        return False
    if spike.cloud != workload.cloud:
        return False
    if spike.usage_account_id and spike.usage_account_id != workload.usage_account_id:
        return False
    if spike.service_name and spike.service_name != workload.service_name:
        return False
    if spike.usage_type and spike.usage_type != workload.usage_type:
        return False
    return spike.application is None or spike.application == workload.application


def matching_spikes(workload: Workload, day: date) -> tuple[Spike, ...]:
    """Return catalog spikes that apply to this workload on this day."""
    return tuple(spike for spike in SPIKES if _spike_matches(spike, workload, day))
