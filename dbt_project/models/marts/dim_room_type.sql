select distinct
    room_type,
    case room_type
        when 'Deluxe Room' then 1
        when 'Superior Cottages' then 2
        when 'Mourya Heritage House' then 3
        when 'Private Pool Villa' then 4
        else 99
    end as tier_rank
from {{ ref('stg_bookings') }}
