select
    vehicle_id,
    cast(reading_date as date) as reading_date,
    odometer_km,
    cycle_count,
    state_of_health_pct,
    pack_temperature_avg_c
from {{ source('raw', 'battery_readings') }}
