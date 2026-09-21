select
    charge_id,
    vehicle_id,
    start_time,
    end_time,
    date_diff('minute', start_time, end_time) as duration_minutes,
    start_soc_pct,
    end_soc_pct,
    end_soc_pct - start_soc_pct as soc_delta_pct,
    energy_kwh,
    round(energy_kwh / nullif(date_diff('minute', start_time, end_time), 0) * 60, 2) as avg_charge_rate_kw,
    charger_type,
    is_fast_charge,
    ambient_temp_c
from {{ ref('stg_charging_sessions') }}
