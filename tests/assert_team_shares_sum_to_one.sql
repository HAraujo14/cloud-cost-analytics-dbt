select
    billing_month,
    sum(share_of_month) as share_sum
from {{ ref('fct_cost_by_team') }}
group by billing_month
having abs(sum(share_of_month) - 1) > 0.000001
