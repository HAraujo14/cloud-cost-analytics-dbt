select identity_line_item_id
from {{ ref('stg_aws_cur') }}
where
    line_item_line_item_type = 'Usage'
    and (
        line_item_unblended_cost < 0
        or line_item_usage_amount < 0
    )
