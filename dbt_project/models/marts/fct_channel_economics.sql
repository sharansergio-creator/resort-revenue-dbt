with nights as (
    select n.* from {{ ref('int_booking_nights') }} n
    inner join {{ ref('dim_date') }} d
        on n.stay_date = d.stay_date
    where n.stay_date <= cast('{{ var("as_of_date") }}' as date)
)
select
    strftime(stay_date, '%Y-%m') as stay_year_month,
    channel_name,
    channel_group,
    count(distinct case when booking_status_group = 'REALIZED' then booking_key end) as realized_room_bookings,
    count(distinct case when booking_status_group = 'CANCELLED' then booking_key end) as cancelled_room_bookings,
    count(case when booking_status_group = 'REALIZED' then 1 end) as realized_room_nights,
    count(case when booking_status_group = 'FUTURE_OTB' then 1 end) as future_otb_room_nights,
    count(case when booking_status_group = 'CANCELLED' then 1 end) as cancelled_room_nights,
    coalesce(sum(case when booking_status_group = 'REALIZED' then night_room_revenue_pre_gst else 0 end), 0.00) as realized_room_revenue_pre_gst,
    -- Distribution cost totals and explicit component breakdown
    coalesce(sum(case when booking_status_group = 'REALIZED' then round(night_room_revenue_pre_gst * effective_distribution_cost_pct, 2) else 0 end), 0.00) as distribution_cost_inr,
    coalesce(sum(case when booking_status_group = 'REALIZED' then round(night_room_revenue_pre_gst * effective_distribution_cost_pct, 2) else 0 end), 0.00) as estimated_distribution_cost,
    coalesce(sum(case when booking_status_group = 'REALIZED' then round(night_room_revenue_pre_gst * base_commission_pct, 2) else 0 end), 0.00) as base_ota_commission_cost,
    coalesce(sum(case when booking_status_group = 'REALIZED' then round(night_room_revenue_pre_gst * base_commission_pct * gst_on_commission_pct, 2) else 0 end), 0.00) as gst_on_commission_cost,
    coalesce(sum(case when booking_status_group = 'REALIZED' then round(night_room_revenue_pre_gst * tcs_tds_pct, 2) else 0 end), 0.00) as tds_tcs_withheld,
    coalesce(sum(case when booking_status_group = 'REALIZED' then round(night_room_revenue_pre_gst * (1.0 - effective_distribution_cost_pct), 2) else 0 end), 0.00) as net_room_revenue_after_ota,
    coalesce(sum(case when booking_status_group = 'CANCELLED' then night_room_revenue_pre_gst else 0 end), 0.00) as cancelled_room_revenue_lost
from nights
group by 1, 2, 3
