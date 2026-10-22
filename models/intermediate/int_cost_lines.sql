with aws_lines as (
    select
        cur.identity_line_item_id as source_line_id,
        'aws' as cloud_provider,
        cur.line_item_usage_start_date as usage_date,
        cast(date_trunc('month', cur.line_item_usage_start_date) as date) as billing_month,
        cur.bill_payer_account_id as billing_account_id,
        cur.line_item_usage_account_id as account_id,
        account_register.account_name,
        lower(cur.line_item_line_item_type) as line_item_type,
        cur.line_item_product_code as service_code,
        cur.product_servicename as service_name,
        cur.line_item_usage_type as usage_type,
        cur.line_item_operation as operation,
        cur.product_region as region,
        cur.line_item_availability_zone as availability_zone,
        cur.line_item_resource_id as resource_id,
        cur.line_item_usage_amount as usage_amount,
        cur.pricing_unit as usage_unit,
        case
            when cur.line_item_line_item_type = 'Usage' then cur.line_item_unblended_cost
            else 0
        end as gross_cost,
        case
            when cur.line_item_line_item_type = 'Credit' then -cur.line_item_unblended_cost
            else 0
        end as credit_amount,
        cur.line_item_currency_code as currency,
        cur.resource_tags_user_team as team,
        cur.resource_tags_user_environment as environment,
        cur.resource_tags_user_cost_center as cost_center,
        cur.resource_tags_user_application as application,
        cur.is_synthetic,
        cur.dataset_label,
        cur.spike_id
    from {{ ref('stg_aws_cur') }} as cur
    inner join {{ ref('accounts') }} as account_register
        on
            account_register.cloud_provider = 'aws'
            and cur.line_item_usage_account_id = account_register.account_id
),

gcp_lines as (
    select
        billing_row_id as source_line_id,
        'gcp' as cloud_provider,
        usage_start_date as usage_date,
        cast(date_trunc('month', usage_start_date) as date) as billing_month,
        billing_account_id,
        project_id as account_id,
        project_name as account_name,
        'usage' as line_item_type,
        service_id as service_code,
        service_description as service_name,
        sku_description as usage_type,
        cast(null as varchar) as operation,
        location_region as region,
        cast(null as varchar) as availability_zone,
        cast(null as varchar) as resource_id,
        usage_amount,
        usage_pricing_unit as usage_unit,
        cost as gross_cost,
        -credits_amount as credit_amount,
        currency,
        label_team as team,
        label_environment as environment,
        label_cost_center as cost_center,
        label_application as application,
        is_synthetic,
        dataset_label,
        spike_id
    from {{ ref('stg_gcp_billing') }}
),

unioned as (
    select * from aws_lines
    union all
    select * from gcp_lines
)

select
    source_line_id,
    cloud_provider,
    usage_date,
    billing_month,
    billing_account_id,
    account_id,
    account_name,
    line_item_type,
    service_code,
    service_name,
    usage_type,
    operation,
    region,
    availability_zone,
    resource_id,
    usage_amount,
    usage_unit,
    gross_cost,
    credit_amount,
    currency,
    team,
    environment,
    cost_center,
    application,
    is_synthetic,
    dataset_label,
    spike_id,
    gross_cost - credit_amount as net_cost
from unioned
