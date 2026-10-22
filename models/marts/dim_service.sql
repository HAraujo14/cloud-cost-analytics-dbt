with services as (
    select
        cloud_provider,
        service_name,
        min(service_code) as service_code
    from {{ ref('int_cost_lines') }}
    group by cloud_provider, service_name
)

select
    {{ surrogate_key(['services.cloud_provider', 'services.service_name']) }} as service_key,
    services.cloud_provider,
    services.service_name,
    services.service_code,
    categories.service_category
from services
inner join {{ ref('service_categories') }} as categories
    on
        services.cloud_provider = categories.cloud_provider
        and services.service_name = categories.service_name
