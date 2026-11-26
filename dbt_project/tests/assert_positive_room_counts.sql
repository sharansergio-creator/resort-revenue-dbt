-- Singular test: verify all room booking records have positive room count (> 0)
select
    room_booking_key,
    booking_total_rooms
from {{ ref('stg_bookings') }}
where booking_total_rooms <= 0 or booking_total_rooms is null
