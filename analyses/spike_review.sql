select
    usage_date,
    cloud_provider,
    account_name,
    service_name,
    net_cost,
    rolling_mean_cost,
    z_score,
    labelled_spike_id
from {{ ref('mart_service_anomalies') }}
where is_cost_spike
order by z_score desc
