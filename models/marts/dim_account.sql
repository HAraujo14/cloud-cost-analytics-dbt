select
    {{ surrogate_key(['account_id', 'cloud_provider']) }} as account_key,
    account_id,
    cloud_provider,
    min(account_name) as account_name,
    min(billing_account_id) as billing_account_id,
    min(environment) as environment,
    min(usage_date) as first_usage_date,
    max(usage_date) as last_usage_date
from {{ ref('int_cost_lines') }}
group by account_id, cloud_provider
