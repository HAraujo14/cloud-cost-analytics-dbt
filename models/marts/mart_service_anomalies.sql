{% set window_days = var('anomaly_window_days', 28) %}
{% set min_history = var('anomaly_min_history_days', 14) %}
{% set z_threshold = var('anomaly_z_threshold', 3) %}
{% set min_lift = var('anomaly_min_lift_ratio', 0.25) %}

with daily as (
    select
        usage_date,
        cloud_provider,
        account_id,
        service_name,
        min(billing_month) as billing_month,
        min(account_name) as account_name,
        sum(net_cost) as net_cost
    from {{ ref('fct_daily_cost') }}
    group by
        usage_date,
        cloud_provider,
        account_id,
        service_name
),

labels as (
    select
        usage_date,
        cloud_provider,
        account_id,
        service_name,
        max(spike_id) as labelled_spike_id
    from {{ ref('int_cost_lines') }}
    group by
        usage_date,
        cloud_provider,
        account_id,
        service_name
),

scored as (
    select
        daily.usage_date,
        daily.billing_month,
        daily.cloud_provider,
        daily.account_id,
        daily.account_name,
        daily.service_name,
        daily.net_cost,
        labels.labelled_spike_id,
        count(daily.net_cost) over (
            partition by daily.cloud_provider, daily.account_id, daily.service_name
            order by daily.usage_date
            rows between {{ window_days }} preceding and 1 preceding
        ) as history_days,
        avg(daily.net_cost) over (
            partition by daily.cloud_provider, daily.account_id, daily.service_name
            order by daily.usage_date
            rows between {{ window_days }} preceding and 1 preceding
        ) as rolling_mean_cost,
        stddev_samp(daily.net_cost) over (
            partition by daily.cloud_provider, daily.account_id, daily.service_name
            order by daily.usage_date
            rows between {{ window_days }} preceding and 1 preceding
        ) as rolling_stddev_cost
    from daily
    inner join labels
        on
            daily.usage_date = labels.usage_date
            and daily.cloud_provider = labels.cloud_provider
            and daily.account_id = labels.account_id
            and daily.service_name = labels.service_name
)

select
    usage_date,
    billing_month,
    cloud_provider,
    account_id,
    account_name,
    service_name,
    net_cost,
    history_days,
    rolling_mean_cost,
    rolling_stddev_cost,
    case
        when history_days >= {{ min_history }}
            then (net_cost - rolling_mean_cost) / nullif(rolling_stddev_cost, 0)
    end as z_score,
    case
        when
            history_days >= {{ min_history }}
            and (net_cost - rolling_mean_cost) / nullif(rolling_stddev_cost, 0)
            >= {{ z_threshold }}
            and (net_cost - rolling_mean_cost) / nullif(rolling_mean_cost, 0)
            >= {{ min_lift }}
            then true
        else false
    end as is_cost_spike,
    labelled_spike_id
from scored
