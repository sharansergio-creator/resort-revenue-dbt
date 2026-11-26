-- Singular test: verify overall property-level realized_occupied_nights reconciles within 0.5% of pms_sold_rooms across historical stay dates
with totals as (
    select
        sum(realized_occupied_nights) as total_realized_nights,
        sum(pms_sold_rooms) as total_pms_sold_rooms
    from {{ ref('fct_daily_property_kpi') }}
    where stay_date <= cast('{{ var("as_of_date") }}' as date)
)
select
    total_realized_nights,
    total_pms_sold_rooms,
    abs(total_realized_nights - total_pms_sold_rooms) as diff_nights,
    round(abs(total_realized_nights - total_pms_sold_rooms) * 1.0 / nullif(total_pms_sold_rooms, 0), 4) as diff_ratio
from totals
where abs(total_realized_nights - total_pms_sold_rooms) * 1.0 / nullif(total_pms_sold_rooms, 0) > 0.005
