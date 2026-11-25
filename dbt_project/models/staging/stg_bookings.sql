with master as (
    select * from {{ source('stayflexi_raw', 'master_bookings') }}
),
rev as (
    select * from {{ source('stayflexi_raw', 'room_revenue') }}
),
joined as (
    select
        m.booking_key,
        cast(m.booking_date as date) as booking_date,
        cast(m.check_in_date as date) as check_in_date,
        cast(m.check_out_date as date) as check_out_date,
        greatest(datediff('day', cast(m.check_in_date as date), cast(m.check_out_date as date)), 1) as length_of_stay,
        greatest(datediff('day', cast(m.booking_date as date), cast(m.check_in_date as date)), 0) as lead_time_days,
        case
            when upper(trim(m.source)) in ('PHONE CALL', 'PHONE_CALL') then 'PHONE CALL'
            when upper(trim(m.source)) in ('WALK-IN BOOKING', 'WALK-IN') then 'WALK-IN'
            else upper(trim(m.source))
        end as channel_name,
        upper(trim(m.booking_status)) as raw_booking_status,
        case
            when upper(trim(m.booking_status)) = 'CANCELLED' then 'CANCELLED'
            when upper(trim(m.booking_status)) in ('CHECKED OUT', 'CHECKED IN') then 'REALIZED'
            when upper(trim(m.booking_status)) in ('CONFIRMED', 'ON_HOLD') and cast(m.check_in_date as date) <= date '2026-11-22' then 'REALIZED'
            when upper(trim(m.booking_status)) in ('CONFIRMED', 'ON_HOLD') then 'FUTURE_OTB'
            else 'OTHER'
        end as booking_status_group,
        coalesce(cast(m.adults as integer), 1) as adults,
        coalesce(cast(m.no_of_rooms as integer), 1) as num_rooms,
        m.room_types as raw_room_types,
        m.rate_plans as raw_rate_plans,
        coalesce(cast(r.room_revenue_inr as decimal(12,2)), 0.00) as booking_room_revenue_pre_gst,
        coalesce(cast(r.room_taxes_inr as decimal(12,2)), 0.00) as booking_room_taxes,
        coalesce(cast(r.services_amt_inr as decimal(12,2)), 0.00) as booking_services_revenue,
        coalesce(cast(r.room_discount as decimal(12,2)), 0.00) as booking_room_discount,
        coalesce(cast(r.total_amt_inr as decimal(12,2)), 0.00) as booking_total_gross_amount,
        coalesce(cast(r.total_refunds_inr as decimal(12,2)), 0.00) as booking_total_refunds,
        coalesce(cast(r.balance_amt_inr as decimal(12,2)), 0.00) as booking_balance_due,
        coalesce(cast(r.room_nights as integer), 0) as pms_reported_room_nights
    from master m
    left join rev r
        on m.booking_key = r.booking_key
),
exploded_rooms as (
    select
        j.*,
        unnest(generate_series(1, j.num_rooms)) as room_seq,
        string_split(coalesce(j.raw_room_types, 'Unknown'), ',') as room_type_arr,
        string_split(coalesce(j.raw_rate_plans, 'Standard'), ',') as rate_plan_arr
    from joined j
)
select
    booking_key || '-R' || cast(room_seq as varchar) as room_booking_key,
    booking_key,
    room_seq,
    num_rooms as booking_total_rooms,
    booking_date,
    check_in_date,
    check_out_date,
    length_of_stay,
    lead_time_days,
    case
        when lead_time_days <= 3 then '0-3d (Last Minute)'
        when lead_time_days <= 14 then '4-14d (Short Window)'
        when lead_time_days <= 30 then '15-30d (Medium Window)'
        else '31d+ (Early Bird)'
    end as lead_time_bucket,
    channel_name,
    raw_booking_status,
    booking_status_group,
    -- Normalize room type case (e.g., 'Private Pool villa' -> 'Private Pool Villa')
    case
        when lower(trim(coalesce(room_type_arr[room_seq], room_type_arr[1]))) = 'private pool villa' then 'Private Pool Villa'
        when lower(trim(coalesce(room_type_arr[room_seq], room_type_arr[1]))) = 'deluxe room' then 'Deluxe Room'
        when lower(trim(coalesce(room_type_arr[room_seq], room_type_arr[1]))) = 'superior cottages' then 'Superior Cottages'
        when lower(trim(coalesce(room_type_arr[room_seq], room_type_arr[1]))) = 'mourya heritage house' then 'Mourya Heritage House'
        else trim(coalesce(room_type_arr[room_seq], room_type_arr[1]))
    end as room_type,
    -- Normalize rate plan aliases
    case
        when upper(trim(coalesce(rate_plan_arr[room_seq], rate_plan_arr[1]))) in ('CP', 'ROOM WITH BREAKFAST', 'BREAKFAST INCLUDED', 'CP LD') then 'CP (Breakfast)'
        when upper(trim(coalesce(rate_plan_arr[room_seq], rate_plan_arr[1]))) in ('MAP', 'HALF BOARD') then 'MAP (Half Board)'
        when upper(trim(coalesce(rate_plan_arr[room_seq], rate_plan_arr[1]))) in ('AP') then 'AP (Full Board)'
        when upper(trim(coalesce(rate_plan_arr[room_seq], rate_plan_arr[1]))) in ('NR-CP', 'NON-REFUNDABLE CP') then 'NR-CP (Non-Refundable)'
        else 'EP / Standard'
    end as rate_plan_clean,
    -- Allocate booking-level financials cleanly across rooms in multi-room bookings (with rounding residual on room 1)
    case
        when room_seq = 1 then round(booking_room_revenue_pre_gst - round(booking_room_revenue_pre_gst / num_rooms, 2) * (num_rooms - 1), 2)
        else round(booking_room_revenue_pre_gst / num_rooms, 2)
    end as room_revenue_pre_gst,
    case
        when room_seq = 1 then round(booking_services_revenue - round(booking_services_revenue / num_rooms, 2) * (num_rooms - 1), 2)
        else round(booking_services_revenue / num_rooms, 2)
    end as services_revenue,
    case
        when room_seq = 1 then round(booking_room_taxes - round(booking_room_taxes / num_rooms, 2) * (num_rooms - 1), 2)
        else round(booking_room_taxes / num_rooms, 2)
    end as room_taxes,
    case
        when room_seq = 1 then round(booking_room_discount - round(booking_room_discount / num_rooms, 2) * (num_rooms - 1), 2)
        else round(booking_room_discount / num_rooms, 2)
    end as room_discount,
    case
        when room_seq = 1 then round(booking_total_refunds - round(booking_total_refunds / num_rooms, 2) * (num_rooms - 1), 2)
        else round(booking_total_refunds / num_rooms, 2)
    end as total_refunds,
    pms_reported_room_nights
from exploded_rooms
