select
    cast(stay_date as date) as stay_date,
    cast(total_rooms as integer) as total_physical_rooms,
    cast(blocked_rooms as integer) as blocked_rooms,
    cast(net_rooms as integer) as net_sellable_rooms,
    cast(sold_rooms as integer) as pms_sold_rooms,
    cast(available_rooms as integer) as pms_available_rooms,
    cast(unassign_count as integer) as unassigned_rooms
from {{ source('stayflexi_raw', 'daily_inventory') }}
