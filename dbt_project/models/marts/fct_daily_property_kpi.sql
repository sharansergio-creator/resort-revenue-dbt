with daily_room as (
    select
        stay_date,
        sum(realized_occupied_nights) as realized_occupied_nights,
        sum(future_otb_nights) as future_otb_nights,
        sum(cancelled_nights) as cancelled_nights,
        sum(realized_room_revenue_pre_gst) as realized_room_revenue_pre_gst,
        sum(realized_services_revenue) as realized_services_revenue,
        sum(realized_distribution_cost) as realized_distribution_cost,
        sum(realized_net_room_revenue) as realized_net_room_revenue,
        sum(future_otb_room_revenue) as future_otb_room_revenue,
        sum(cancelled_room_revenue_lost) as cancelled_room_revenue_lost
    from {{ ref('fct_daily_room_performance') }}
    group by 1
)
select
    inv.stay_date,
    inv.total_physical_rooms,
    inv.blocked_rooms,
    inv.net_sellable_rooms,
    inv.pms_sold_rooms,
    inv.pms_available_rooms,
    coalesce(r.realized_occupied_nights, 0) as realized_occupied_nights,
    coalesce(r.future_otb_nights, 0) as future_otb_nights,
    coalesce(r.cancelled_nights, 0) as cancelled_nights,
    coalesce(r.realized_room_revenue_pre_gst, 0.00) as realized_room_revenue_pre_gst,
    coalesce(r.realized_services_revenue, 0.00) as realized_services_revenue,
    coalesce(r.realized_distribution_cost, 0.00) as realized_distribution_cost,
    coalesce(r.realized_net_room_revenue, 0.00) as realized_net_room_revenue,
    coalesce(r.future_otb_room_revenue, 0.00) as future_otb_room_revenue,
    coalesce(r.cancelled_room_revenue_lost, 0.00) as cancelled_room_revenue_lost
from {{ ref('stg_daily_inventory') }} inv
left join daily_room r
    on inv.stay_date = r.stay_date
