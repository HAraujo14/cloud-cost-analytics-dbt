with bounds as (
    select
        min(usage_date) as min_date,
        max(usage_date) as max_date
    from {{ ref('int_cost_lines') }}
),

date_spine as (
    select cast(day_series.generate_series as date) as date_day
    from bounds
    cross join generate_series(
        bounds.min_date,
        bounds.max_date,
        interval 1 day
    ) as day_series
)

select
    date_spine.date_day,
    cast(date_trunc('month', date_spine.date_day) as date) as billing_month,
    case isodow(date_spine.date_day)
        when 1 then 'Monday'
        when 2 then 'Tuesday'
        when 3 then 'Wednesday'
        when 4 then 'Thursday'
        when 5 then 'Friday'
        when 6 then 'Saturday'
        when 7 then 'Sunday'
    end as day_name,
    isodow(date_spine.date_day) as iso_day_of_week,
    isodow(date_spine.date_day) in (6, 7) as is_weekend
from date_spine
