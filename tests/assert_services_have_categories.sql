select distinct
    cost_lines.cloud_provider,
    cost_lines.service_name
from {{ ref('int_cost_lines') }} as cost_lines
left join {{ ref('dim_service') }} as services
    on
        cost_lines.cloud_provider = services.cloud_provider
        and cost_lines.service_name = services.service_name
where
    services.service_key is null
    or services.service_category is null
