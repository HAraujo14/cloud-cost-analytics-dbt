with monthly as (
    select * from {{ ref('fct_cost_mom') }}
)

select
    current_month.billing_month,
    current_month.cloud_provider,
    current_month.account_id,
    current_month.service_name
from monthly as current_month
inner join monthly as prior_month
    on
        current_month.cloud_provider = prior_month.cloud_provider
        and current_month.account_id = prior_month.account_id
        and current_month.service_name = prior_month.service_name
        and current_month.billing_month = prior_month.billing_month + interval 1 month
where
    current_month.prev_month_net_cost is null
    or abs(current_month.prev_month_net_cost - prior_month.net_cost) > 0.000001
