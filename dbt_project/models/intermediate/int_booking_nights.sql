with bookings as (
    select
        b.*,
        coalesce(c.channel_group, 'Direct') as channel_group,
        coalesce(c.base_commission_pct, 0.0) as base_commission_pct,
        coalesce(c.gst_on_commission_pct, 0.0) as gst_on_commission_pct,
        coalesce(c.tcs_tds_pct, 0.0) as tcs_tds_pct,
        round(
            coalesce(c.base_commission_pct, 0.0) * (1.0 + coalesce(c.gst_on_commission_pct, 0.0))
            + coalesce(c.tcs_tds_pct, 0.0),
            4
        ) as effective_distribution_cost_pct
    from {{ ref('stg_bookings') }} b
    left join {{ ref('channel_commission_rates') }} c
        on b.channel_name = c.channel_name
        and b.booking_date between cast(c.effective_from as date) and cast(c.effective_to as date)
),
exploded as (
    select
        *,
        unnest(generate_series(0, length_of_stay - 1)) as night_index
    from bookings
)
select
    room_booking_key || '_' || strftime(check_in_date + cast(night_index as integer), '%Y%m%d') as booking_night_key,
    room_booking_key,
    booking_key,
    room_seq,
    night_index + 1 as night_number,
    length_of_stay,
    booking_date,
    check_in_date,
    check_out_date,
    cast(check_in_date + cast(night_index as integer) as date) as stay_date,
    lead_time_days,
    lead_time_bucket,
    channel_name,
    channel_group,
    raw_booking_status,
    booking_status_group,
    room_type,
    rate_plan_clean,
    effective_distribution_cost_pct,
    -- Allocate room revenue evenly in paise with exact residual on final stay night
    case
        when night_index + 1 = length_of_stay
            then round(room_revenue_pre_gst - round(room_revenue_pre_gst / length_of_stay, 2) * (length_of_stay - 1), 2)
        else round(room_revenue_pre_gst / length_of_stay, 2)
    end as night_room_revenue_pre_gst,
    case
        when night_index + 1 = length_of_stay
            then round(services_revenue - round(services_revenue / length_of_stay, 2) * (length_of_stay - 1), 2)
        else round(services_revenue / length_of_stay, 2)
    end as night_services_revenue,
    case
        when night_index + 1 = length_of_stay
            then round(room_taxes - round(room_taxes / length_of_stay, 2) * (length_of_stay - 1), 2)
        else round(room_taxes / length_of_stay, 2)
    end as night_room_taxes
from exploded
