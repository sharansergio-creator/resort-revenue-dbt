with nights as (
    select * from {{ ref('int_booking_nights') }}
),
spine as (
    select
        d.stay_date,
        r.room_type
    from {{ ref('dim_date') }} d
    cross join {{ ref('dim_room_type') }} r
),
agg as (
    select
        stay_date,
        room_type,
        count(case when booking_status_group = 'REALIZED' then 1 end) as realized_occupied_nights,
        count(case when booking_status_group = 'FUTURE_OTB' then 1 end) as future_otb_nights,
        count(case when booking_status_group = 'CANCELLED' then 1 end) as cancelled_nights,
        coalesce(sum(case when booking_status_group = 'REALIZED' then night_room_revenue_pre_gst else 0 end), 0.00) as realized_room_revenue_pre_gst,
        coalesce(sum(case when booking_status_group = 'REALIZED' then night_services_revenue else 0 end), 0.00) as realized_services_revenue,
        coalesce(sum(case when booking_status_group = 'REALIZED' then round(night_room_revenue_pre_gst * effective_distribution_cost_pct, 2) else 0 end), 0.00) as realized_distribution_cost,
        coalesce(sum(case when booking_status_group = 'REALIZED' then round(night_room_revenue_pre_gst * (1.0 - effective_distribution_cost_pct), 2) else 0 end), 0.00) as realized_net_room_revenue,
        coalesce(sum(case when booking_status_group = 'FUTURE_OTB' then night_room_revenue_pre_gst else 0 end), 0.00) as future_otb_room_revenue,
        coalesce(sum(case when booking_status_group = 'CANCELLED' then night_room_revenue_pre_gst else 0 end), 0.00) as cancelled_room_revenue_lost
    from nights
    group by 1, 2
)
select
    s.stay_date,
    s.room_type,
    coalesce(a.realized_occupied_nights, 0) as realized_occupied_nights,
    coalesce(a.future_otb_nights, 0) as future_otb_nights,
    coalesce(a.cancelled_nights, 0) as cancelled_nights,
    coalesce(a.realized_room_revenue_pre_gst, 0.00) as realized_room_revenue_pre_gst,
    coalesce(a.realized_services_revenue, 0.00) as realized_services_revenue,
    coalesce(a.realized_distribution_cost, 0.00) as realized_distribution_cost,
    coalesce(a.realized_net_room_revenue, 0.00) as realized_net_room_revenue,
    coalesce(a.future_otb_room_revenue, 0.00) as future_otb_room_revenue,
    coalesce(a.cancelled_room_revenue_lost, 0.00) as cancelled_room_revenue_lost
from spine s
left join agg a
    on s.stay_date = a.stay_date
    and s.room_type = a.room_type
