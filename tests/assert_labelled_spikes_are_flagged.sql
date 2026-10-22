-- Every account-service-day that carries an injected spike id should clear
-- the z-score screen. The generator's multipliers are sized for that.
select
    usage_date,
    cloud_provider,
    account_id,
    service_name,
    labelled_spike_id,
    z_score,
    net_cost,
    rolling_mean_cost
from {{ ref('mart_service_anomalies') }}
where
    labelled_spike_id is not null
    and not is_cost_spike
