select
    b.room_booking_key,
    b.booking_key,
    b.room_seq,
    b.booking_total_rooms,
    b.booking_date,
    b.check_in_date,
    b.check_out_date,
    b.length_of_stay,
    b.lead_time_days,
    b.lead_time_bucket,
    b.channel_name,
    coalesce(c.channel_group, 'Direct') as channel_group,
    b.raw_booking_status,
    b.booking_status_group,
    case when b.booking_status_group = 'CANCELLED' then 1 else 0 end as is_cancelled,
    b.room_type,
    b.rate_plan_clean,
    b.room_revenue_pre_gst,
    b.services_revenue,
    b.room_taxes,
    b.room_discount,
    b.total_refunds,
    round(b.room_revenue_pre_gst * coalesce(c.effective_distribution_cost_pct, 0.0), 2) as estimated_distribution_cost,
    round(b.room_revenue_pre_gst * (1.0 - coalesce(c.effective_distribution_cost_pct, 0.0)), 2) as net_room_revenue_after_ota
from {{ ref('stg_bookings') }} b
left join {{ ref('dim_channel') }} c
    on b.channel_name = c.channel_name
