select
    vehicle_id,
    model,
    battery_capacity_kwh,
    region,
    cast(manufacture_date as date) as manufacture_date,
    fast_charge_fraction
from {{ source('raw', 'vehicles') }}
