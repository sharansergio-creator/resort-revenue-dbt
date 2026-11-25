-- Singular test: realized daily occupied rooms must never exceed net sellable rooms
select
    stay_date,
    realized_occupied_nights,
    net_sellable_rooms
from {{ ref('fct_daily_property_kpi') }}
where realized_occupied_nights > net_sellable_rooms
