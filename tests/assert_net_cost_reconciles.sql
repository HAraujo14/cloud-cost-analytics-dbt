with expected as (
    select
        usage_date,
        cloud_provider,
        account_id,
        service_name,
        usage_type,
        usage_unit,
        region,
        team,
        environment,
        cost_center,
        application,
        sum(gross_cost) as gross_cost,
        sum(credit_amount) as credit_amount,
        sum(gross_cost) - sum(credit_amount) as net_cost,
        sum(usage_amount) as usage_amount
    from {{ ref('int_cost_lines') }}
    group by
        usage_date,
        cloud_provider,
        account_id,
        service_name,
        usage_type,
        usage_unit,
        region,
        team,
        environment,
        cost_center,
        application
)

select
    expected.usage_date,
    expected.account_id,
    expected.service_name,
    expected.usage_type
from expected
left join {{ ref('fct_daily_cost') }} as actual
    on
        expected.usage_date = actual.usage_date
        and expected.cloud_provider = actual.cloud_provider
        and expected.account_id = actual.account_id
        and expected.service_name = actual.service_name
        and expected.usage_type = actual.usage_type
        and expected.usage_unit = actual.usage_unit
        and expected.region = actual.region
        and expected.team = actual.team
        and expected.environment = actual.environment
        and expected.cost_center = actual.cost_center
        and expected.application = actual.application
where
    actual.daily_cost_key is null
    or abs(expected.net_cost - actual.net_cost) > 0.000001
    or abs(expected.gross_cost - actual.gross_cost) > 0.000001
    or abs(expected.credit_amount - actual.credit_amount) > 0.000001
    or abs(expected.usage_amount - actual.usage_amount) > 0.000001
