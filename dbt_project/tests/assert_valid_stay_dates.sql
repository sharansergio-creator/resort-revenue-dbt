-- Singular test: verify check_out_date is strictly after check_in_date
select
    room_booking_key,
    check_in_date,
    check_out_date
from {{ ref('stg_bookings') }}
where check_out_date <= check_in_date
