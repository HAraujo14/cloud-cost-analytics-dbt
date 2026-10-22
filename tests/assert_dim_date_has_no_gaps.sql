with ordered_dates as (
    select
        date_day,
        lead(date_day) over (order by date_day) as next_date
    from {{ ref('dim_date') }}
)

select
    date_day,
    next_date
from ordered_dates
where
    next_date is not null
    and next_date <> date_day + interval 1 day
