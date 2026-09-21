-- Grain: one row per vehicle per battery-telemetry snapshot (~every 3 days).

select
    r.vehicle_id,
    v.vehicle_sk,
    r.reading_date,
    r.odometer_km,
    r.cycle_count,
    r.state_of_health_pct,
    r.pack_temperature_avg_c,
    date_diff('day', v.manufacture_date, r.reading_date) as age_days
from {{ ref('stg_battery_readings') }} r
inner join {{ ref('dim_vehicles') }} v on r.vehicle_id = v.vehicle_id
