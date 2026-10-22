# Synthetic cloud cost summary

> Synthetic data (`synthetic-finops-portfolio`). These figures are
> computed from the generated extract. They are not real cloud spend.

## Window

- Usage dates: 2026-04-01 through 2026-09-30
- Daily fact rows: 6,405
- Gross cost: $139,327.98
- Credits (positive magnitude): $5,690.90
- Net cost: $133,637.08

Extract row counts:

| extract | rows |
| --- | --- |
| aws_cur | 7,869 |
| gcp_billing | 5,124 |

Net cost by cloud, full window:

| cloud | net cost | gross cost |
| --- | --- | --- |
| aws | $86,268.94 | $90,065.50 |
| gcp | $47,368.14 | $49,262.48 |

## Latest month (2026-09)

Net cost by team:

| team | net cost |
| --- | --- |
| data-platform | $13,344.67 |
| product-backend | $6,373.48 |
| shared-services | $2,554.88 |
| ml-platform | $577.21 |
| finops | $103.17 |

Largest services:

| cloud | service | net cost |
| --- | --- | --- |
| aws | Amazon Elastic Compute Cloud | $5,393.06 |
| aws | Amazon Simple Storage Service | $4,274.42 |
| gcp | BigQuery | $2,637.03 |
| gcp | Cloud Storage | $2,084.68 |
| gcp | Compute Engine | $1,825.77 |
| aws | Amazon Relational Database Service | $1,697.94 |
| aws | AWS Lambda | $1,210.84 |
| aws | Amazon CloudWatch | $962.84 |

Largest month-over-month service moves (summed across accounts):

| cloud | service | this month | prior month | change |
| --- | --- | --- | --- | --- |
| aws | Amazon Virtual Private Cloud | $629.24 | $811.57 | -22.5% |
| aws | Amazon Simple Storage Service | $4,274.42 | $4,162.83 | 2.7% |
| gcp | BigQuery | $2,637.03 | $2,536.49 | 4.0% |
| gcp | Cloud Storage | $2,084.68 | $2,023.39 | 3.0% |
| aws | Amazon CloudWatch | $962.84 | $987.38 | -2.5% |
| aws | AWS Lambda | $1,210.84 | $1,191.00 | 1.7% |
| aws | Amazon Relational Database Service | $1,697.94 | $1,714.64 | -1.0% |
| gcp | Cloud SQL | $461.92 | $478.06 | -3.4% |

## Anomaly screen

Rolling 28-day z-score of daily net cost by account and service.
A day is flagged when at least 14 prior days exist, z >= 3,
and net cost is at least 25% above the trailing mean.
On this generated dataset:

- Labelled spike account-service-days: 7
- Of those, flagged by the screen: 7
- Flagged days in total: 7
- Flagged days with no injected spike label: 0

Flagged days, highest z-score first:

| date | cloud | account | service | net cost | baseline | z | spike |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-05-12 | aws | aws-sandbox | Amazon Elastic Compute Cloud | $32.67 | $1.97 | 57.80 | syn-sandbox-ec2 |
| 2026-08-18 | aws | aws-prod-platform | Amazon Virtual Private Cloud | $120.72 | $20.21 | 42.89 | syn-nat-cross-az |
| 2026-06-09 | aws | aws-prod-platform | Amazon Elastic Compute Cloud | $478.07 | $117.41 | 31.16 | syn-ec2-autoscale |
| 2026-07-21 | gcp | gcp-prod-analytics | BigQuery | $492.19 | $78.16 | 23.53 | syn-bq-full-scan |
| 2026-06-10 | aws | aws-prod-platform | Amazon Elastic Compute Cloud | $455.67 | $130.01 | 4.71 | syn-ec2-autoscale |
| 2026-08-19 | aws | aws-prod-platform | Amazon Virtual Private Cloud | $112.54 | $23.69 | 4.64 | syn-nat-cross-az |
| 2026-06-11 | aws | aws-prod-platform | Amazon Elastic Compute Cloud | $457.62 | $141.98 | 3.41 | syn-ec2-autoscale |

## Unit cost

Spikes in this dataset scale usage and price together, so unit cost
stays near the anchor rate. Credits lower the net unit cost.
Averages for 2026-09, largest services first:

| service | usage type | unit | gross unit cost | net unit cost |
| --- | --- | --- | --- | --- |
| Amazon Simple Storage Service | TimedStorage-ByteHrs | GB-Month | 0.023000 | 0.023000 |
| Amazon Elastic Compute Cloud | BoxUsage:m6i.xlarge | hours | 0.192000 | 0.168960 |
| Cloud Storage | Standard Storage | GB-Month | 0.020000 | 0.020000 |
| Compute Engine | e2-standard-4 | hours | 0.134000 | 0.114367 |
| BigQuery | Analysis | TiB | 6.250000 | 6.250000 |
| Amazon Elastic Compute Cloud | BoxUsage:m6i.2xlarge | hours | 0.384000 | 0.353280 |
| BigQuery | Active Logical Storage | GB-Month | 0.020000 | 0.020000 |
| AWS Lambda | USE1-Lambda-GB-Second | GB-Seconds | 0.000017 | 0.000017 |

## Forecast

Method: OLS trend plus an additive weekday residual.
Spike days flagged above are left out of the fit.
The band is +/- 1.96 residual standard deviations.
It is illustrative, not a calibrated prediction interval.
Holdout MAPE is only a backtest on this synthetic series.

| series | holdout MAPE | MAPE excluding spike days | slope per day |
| --- | --- | --- | --- |
| total | 2.2% | 2.2% | 0.44 |
| aws | 1.8% | 1.8% | 0.27 |
| gcp | 2.2% | 2.2% | 0.17 |

Next 7 forecast days:

| series | date | forecast net cost | lower band | upper band |
| --- | --- | --- | --- | --- |
| aws | 2026-10-01 | $521.19 | $508.92 | $533.46 |
| aws | 2026-10-02 | $523.16 | $510.89 | $535.43 |
| aws | 2026-10-03 | $404.53 | $392.26 | $416.80 |
| aws | 2026-10-04 | $404.16 | $391.89 | $416.43 |
| aws | 2026-10-05 | $523.40 | $511.13 | $535.67 |
| aws | 2026-10-06 | $522.81 | $510.55 | $535.08 |
| aws | 2026-10-07 | $522.82 | $510.55 | $535.09 |
| gcp | 2026-10-01 | $289.95 | $281.78 | $298.13 |
| gcp | 2026-10-02 | $290.34 | $282.17 | $298.52 |
| gcp | 2026-10-03 | $227.48 | $219.31 | $235.66 |
| gcp | 2026-10-04 | $226.99 | $218.81 | $235.16 |
| gcp | 2026-10-05 | $291.33 | $283.16 | $299.51 |
| gcp | 2026-10-06 | $292.59 | $284.42 | $300.77 |
| gcp | 2026-10-07 | $290.99 | $282.82 | $299.17 |
| total | 2026-10-01 | $810.16 | $793.06 | $827.27 |
| total | 2026-10-02 | $812.60 | $795.49 | $829.71 |
| total | 2026-10-03 | $631.11 | $614.00 | $648.22 |
| total | 2026-10-04 | $630.25 | $613.14 | $647.36 |
| total | 2026-10-05 | $813.83 | $796.72 | $830.94 |
| total | 2026-10-06 | $814.51 | $797.40 | $831.62 |
| total | 2026-10-07 | $812.73 | $795.62 | $829.84 |

Regenerate with `make report` after `make build`.
