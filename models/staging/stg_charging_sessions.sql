select
    charge_id,
    vehicle_id,
    cast(start_time as timestamp) as start_time,
    cast(end_time as timestamp) as end_time,
    start_soc_pct,
    end_soc_pct,
    energy_kwh,
    charger_type,
    charger_type = 'DC_FAST' as is_fast_charge,
    ambient_temp_c
from {{ source('raw', 'charging_sessions') }}
