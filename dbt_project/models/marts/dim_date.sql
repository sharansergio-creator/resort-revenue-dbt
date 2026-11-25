with bounds as (
    select
        min(stay_date) as min_date,
        max(stay_date) as max_date
    from {{ ref('stg_daily_inventory') }}
),
date_spine as (
    select
        cast(unnest(generate_series(min_date, max_date, interval '1 day')) as date) as stay_date
    from bounds
)
select
    stay_date,
    extract(year from stay_date) as stay_year,
    extract(month from stay_date) as stay_month_num,
    strftime(stay_date, '%Y-%m') as stay_year_month,
    strftime(stay_date, '%b %Y') as stay_month_label,
    dayname(stay_date) as day_name,
    isodow(stay_date) as iso_day_of_week,
    -- Friday (5) and Saturday (6) nights are peak weekend stay nights for resorts
    case when isodow(stay_date) in (5, 6) then true else false end as is_weekend_night,
    case when isodow(stay_date) in (5, 6) then 'Weekend (Fri-Sat)' else 'Weekday (Sun-Thu)' end as day_type,
    case
        when extract(month from stay_date) in (12, 1) then 'Peak Winter & Holiday'
        when extract(month from stay_date) in (4, 5) then 'Peak Summer Vacation'
        when extract(month from stay_date) in (7, 8, 9) then 'Monsoon Off-Season'
        else 'Shoulder Season'
    end as coorg_season
from date_spine
