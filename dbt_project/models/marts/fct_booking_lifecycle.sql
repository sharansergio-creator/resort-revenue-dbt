with booking_level as (
    select
        b.booking_key,
        max(b.booking_total_rooms) as booking_total_rooms,
        min(b.booking_date) as booking_date,
        min(b.check_in_date) as check_in_date,
        min(b.check_out_date) as check_out_date,
        max(b.length_of_stay) as length_of_stay,
        max(b.lead_time_days) as lead_time_days,
        min(b.lead_time_bucket) as lead_time_bucket,
        min(b.channel_name) as channel_name,
        coalesce(min(c.channel_group), 'Direct') as channel_group,
        min(b.raw_booking_status) as raw_booking_status,
        min(b.booking_status_group) as booking_status_group,
        case when min(b.booking_status_group) = 'CANCELLED' then 1 else 0 end as is_cancelled,
        min(case when b.room_seq = 1 then b.room_type end) as room_type,
        min(case when b.room_seq = 1 then b.rate_plan_clean end) as rate_plan_clean,
        sum(b.room_revenue_pre_gst) as room_revenue_pre_gst,
        sum(b.services_revenue) as services_revenue,
        sum(b.room_taxes) as room_taxes,
        sum(b.room_discount) as room_discount,
        sum(b.total_refunds) as total_refunds,
        round(sum(b.room_revenue_pre_gst) * coalesce(min(c.effective_distribution_cost_pct), 0.0), 2) as estimated_distribution_cost,
        round(sum(b.room_revenue_pre_gst) * (1.0 - coalesce(min(c.effective_distribution_cost_pct), 0.0)), 2) as net_room_revenue_after_ota
    from {{ ref('stg_bookings') }} b
    left join {{ ref('dim_channel') }} c
        on b.channel_name = c.channel_name
    group by b.booking_key
)
select * from booking_level
