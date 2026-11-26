-- Singular test: verify 1-to-1 join cardinality between master bookings and exploded room sequences
select
    booking_key,
    room_seq,
    count(*) as record_count
from {{ ref('stg_bookings') }}
group by 1, 2
having count(*) > 1
