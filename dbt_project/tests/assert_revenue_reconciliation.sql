-- Singular test: verify night-level allocated revenue reconciles to booking-level pre-GST room revenue within 0.01 INR
with night_sums as (
    select
        room_booking_key,
        sum(night_room_revenue_pre_gst) as sum_night_rev
    from {{ ref('int_booking_nights') }}
    group by 1
)
select
    b.room_booking_key,
    b.room_revenue_pre_gst,
    n.sum_night_rev,
    abs(b.room_revenue_pre_gst - n.sum_night_rev) as diff
from {{ ref('stg_bookings') }} b
join night_sums n
    on b.room_booking_key = n.room_booking_key
where abs(b.room_revenue_pre_gst - n.sum_night_rev) > 0.01
