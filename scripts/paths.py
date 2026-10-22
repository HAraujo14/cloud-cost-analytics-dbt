"""Repository paths shared by the generator, forecast, and report."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
AWS_CUR_PATH = RAW_DIR / "aws_cur.parquet"
GCP_BILLING_PATH = RAW_DIR / "gcp_billing.parquet"
MANIFEST_PATH = RAW_DIR / "generation_manifest.json"
SEED_PATH = ROOT / "seeds" / "service_categories.csv"
ACCOUNT_SEED_PATH = ROOT / "seeds" / "accounts.csv"
WAREHOUSE_PATH = ROOT / "data" / "warehouse" / "finops.duckdb"
FORECAST_DIR = ROOT / "data" / "forecast"
FORECAST_CSV = FORECAST_DIR / "daily_cost_forecast.csv"
FORECAST_META = FORECAST_DIR / "forecast_meta.json"
REPORT_MD = ROOT / "reports" / "cost_summary.md"
REPORT_HTML = ROOT / "reports" / "cost_summary.html"
