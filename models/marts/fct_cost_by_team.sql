with monthly as (
    select
        billing_month,
        team,
        environment,
        cost_center,
        cloud_provider,
        sum(gross_cost) as gross_cost,
        sum(credit_amount) as credit_amount,
        sum(net_cost) as net_cost
    from {{ ref('fct_daily_cost') }}
    group by
        billing_month,
        team,
        environment,
        cost_center,
        cloud_provider
)

select
    billing_month,
    team,
    environment,
    cost_center,
    cloud_provider,
    gross_cost,
    credit_amount,
    net_cost,
    net_cost / nullif(
        sum(net_cost) over (partition by billing_month),
        0
    ) as share_of_month
from monthly
