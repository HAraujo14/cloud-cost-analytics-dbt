select
    usage_date,
    billing_month,
    cloud_provider,
    account_id,
    service_name,
    usage_type,
    usage_unit,
    region,
    sum(usage_amount) as usage_amount,
    sum(gross_cost) as gross_cost,
    sum(credit_amount) as credit_amount,
    sum(net_cost) as net_cost,
    sum(gross_cost) / nullif(sum(usage_amount), 0) as gross_unit_cost,
    sum(net_cost) / nullif(sum(usage_amount), 0) as net_unit_cost
from {{ ref('fct_daily_cost') }}
group by
    usage_date,
    billing_month,
    cloud_provider,
    account_id,
    service_name,
    usage_type,
    usage_unit,
    region
