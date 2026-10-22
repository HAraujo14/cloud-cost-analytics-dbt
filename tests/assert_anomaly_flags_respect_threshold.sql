select
    usage_date,
    cloud_provider,
    account_id,
    service_name,
    z_score,
    history_days
from {{ ref('mart_service_anomalies') }}
where
    is_cost_spike
    and (
        z_score < {{ var('anomaly_z_threshold', 3) }}
        or history_days < {{ var('anomaly_min_history_days', 14) }}
        or z_score is null
        or (net_cost - rolling_mean_cost) / nullif(rolling_mean_cost, 0)
        < {{ var('anomaly_min_lift_ratio', 0.25) }}
    )
