-- Usage cost, credit magnitude, and net cost stay non-negative.
-- AWS credits are stored as a positive magnitude after staging.
select daily_cost_key
from {{ ref('fct_daily_cost') }}
where
    gross_cost < 0
    or credit_amount < 0
    or net_cost < 0
    or usage_amount < 0
