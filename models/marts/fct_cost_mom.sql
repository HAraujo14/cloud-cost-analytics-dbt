with monthly as (
    select
        billing_month,
        cloud_provider,
        account_id,
        service_name,
        min(account_name) as account_name,
        sum(net_cost) as net_cost
    from {{ ref('fct_daily_cost') }}
    group by
        billing_month,
        cloud_provider,
        account_id,
        service_name
),

lagged as (
    select
        billing_month,
        cloud_provider,
        account_id,
        account_name,
        service_name,
        net_cost,
        lag(net_cost) over (
            partition by cloud_provider, account_id, service_name
            order by billing_month
        ) as prev_month_net_cost
    from monthly
)

select
    billing_month,
    cloud_provider,
    account_id,
    account_name,
    service_name,
    net_cost,
    prev_month_net_cost,
    net_cost - prev_month_net_cost as mom_change_amount,
    case
        when prev_month_net_cost is null or prev_month_net_cost = 0 then null
        else (net_cost - prev_month_net_cost) / prev_month_net_cost
    end as mom_change_ratio
from lagged
