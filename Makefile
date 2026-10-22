.DEFAULT_GOAL := help

PYTHON ?= python3
DBT ?= dbt
export DBT_PROFILES_DIR := $(CURDIR)

.PHONY: help setup generate build test lint forecast report ci clean

help:
	@echo "FinOps cost analytics (synthetic data, dbt, DuckDB)"
	@echo "  make setup      install Python dependencies"
	@echo "  make generate   write synthetic AWS CUR and GCP billing extracts"
	@echo "  make build      generate data, then dbt build (run + test)"
	@echo "  make test       pytest"
	@echo "  make lint       ruff and sqlfluff"
	@echo "  make forecast   fit the local cost forecast from the warehouse"
	@echo "  make report     forecast plus markdown/HTML summary"
	@echo "  make ci         lint, pytest, generate, dbt build, forecast, report"
	@echo "  make clean      remove dbt artifacts and the local warehouse"

setup:
	$(PYTHON) -m pip install -r requirements.txt

generate:
	$(PYTHON) -m scripts.generate_billing

build: generate
	$(DBT) build --target dev

test:
	$(PYTHON) -m pytest -q

lint:
	$(PYTHON) -m ruff check scripts tests
	$(PYTHON) -m ruff format --check scripts tests
	$(PYTHON) -m sqlfluff lint models macros tests analyses

forecast:
	$(PYTHON) -m scripts.forecast_cost

report: forecast
	$(PYTHON) -m scripts.render_report

ci:
	$(PYTHON) -m ruff check scripts tests
	$(PYTHON) -m ruff format --check scripts tests
	$(PYTHON) -m pytest -q
	$(PYTHON) -m scripts.generate_billing
	$(DBT) build --target ci
	$(PYTHON) -m sqlfluff lint models macros tests analyses
	$(PYTHON) -m scripts.forecast_cost
	$(PYTHON) -m scripts.render_report

clean:
	rm -rf target logs dbt_packages
	rm -f data/warehouse/*.duckdb data/warehouse/*.wal data/warehouse/*.duckdb.wal
	rm -f data/raw/*.parquet
