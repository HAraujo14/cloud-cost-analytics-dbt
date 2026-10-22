with staging_counts as (
    select
        'aws' as cloud_provider,
        count(*) as row_count
    from {{ ref('stg_aws_cur') }}
    union all
    select
        'gcp' as cloud_provider,
        count(*) as row_count
    from {{ ref('stg_gcp_billing') }}
),

conformed_counts as (
    select
        cloud_provider,
        count(*) as row_count
    from {{ ref('int_cost_lines') }}
    group by cloud_provider
)

select
    staging_counts.cloud_provider,
    staging_counts.row_count as staging_rows,
    conformed_counts.row_count as conformed_rows
from staging_counts
left join conformed_counts
    on staging_counts.cloud_provider = conformed_counts.cloud_provider
where
    conformed_counts.row_count is null
    or staging_counts.row_count <> conformed_counts.row_count
