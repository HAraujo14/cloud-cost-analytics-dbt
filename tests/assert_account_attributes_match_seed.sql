select
    cost_lines.cloud_provider,
    cost_lines.account_id,
    cost_lines.account_name,
    cost_lines.environment
from {{ ref('int_cost_lines') }} as cost_lines
inner join {{ ref('accounts') }} as account_register
    on
        cost_lines.cloud_provider = account_register.cloud_provider
        and cost_lines.account_id = account_register.account_id
where
    cost_lines.account_name <> account_register.account_name
    or cost_lines.environment <> account_register.environment
