-- GCP export convention: cost is pre-credit and credits.amount is negative or zero.
select billing_row_id
from {{ ref('stg_gcp_billing') }}
where
    cost < 0
    or credits_amount > 0
    or usage_amount < 0
