with source_data as (
    select * from {{ source('cloud_billing', 'aws_cur') }}
)

select
    cast(source_data.identity_line_item_id as varchar) as identity_line_item_id,
    cast(source_data.identity_time_interval as varchar) as identity_time_interval,
    cast(source_data.bill_billing_entity as varchar) as bill_billing_entity,
    cast(source_data.bill_bill_type as varchar) as bill_bill_type,
    cast(source_data.bill_payer_account_id as varchar) as bill_payer_account_id,
    cast(source_data.bill_billing_period_start_date as date) as bill_billing_period_start_date,
    cast(source_data.bill_billing_period_end_date as date) as bill_billing_period_end_date,
    cast(source_data.line_item_usage_account_id as varchar) as line_item_usage_account_id,
    cast(source_data.line_item_line_item_type as varchar) as line_item_line_item_type,
    cast(source_data.line_item_usage_start_date as date) as line_item_usage_start_date,
    cast(source_data.line_item_usage_end_date as date) as line_item_usage_end_date,
    cast(source_data.line_item_product_code as varchar) as line_item_product_code,
    cast(source_data.line_item_usage_type as varchar) as line_item_usage_type,
    cast(source_data.line_item_operation as varchar) as line_item_operation,
    cast(source_data.line_item_availability_zone as varchar) as line_item_availability_zone,
    cast(source_data.line_item_resource_id as varchar) as line_item_resource_id,
    cast(source_data.line_item_usage_amount as double) as line_item_usage_amount,
    cast(source_data.line_item_unblended_rate as double) as line_item_unblended_rate,
    cast(source_data.line_item_unblended_cost as double) as line_item_unblended_cost,
    cast(source_data.line_item_net_unblended_cost as double) as line_item_net_unblended_cost,
    cast(source_data.line_item_currency_code as varchar) as line_item_currency_code,
    cast(source_data.line_item_line_item_description as varchar) as line_item_line_item_description,
    cast(source_data.product_servicecode as varchar) as product_servicecode,
    cast(source_data.product_servicename as varchar) as product_servicename,
    cast(source_data.product_region as varchar) as product_region,
    cast(source_data.product_sku as varchar) as product_sku,
    cast(source_data.pricing_unit as varchar) as pricing_unit,
    cast(source_data.resource_tags_user_team as varchar) as resource_tags_user_team,
    cast(source_data.resource_tags_user_environment as varchar)
        as resource_tags_user_environment,
    cast(source_data.resource_tags_user_cost_center as varchar)
        as resource_tags_user_cost_center,
    cast(source_data.resource_tags_user_application as varchar)
        as resource_tags_user_application,
    cast(source_data._synthetic as boolean) as is_synthetic,
    cast(source_data._dataset_label as varchar) as dataset_label,
    nullif(cast(source_data._spike_id as varchar), '') as spike_id
from source_data
