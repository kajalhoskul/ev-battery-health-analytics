-- Grain: one row per charging session.

select
    s.charge_id,
    s.vehicle_id,
    v.vehicle_sk,
    s.start_time,
    s.end_time,
    s.duration_minutes,
    s.start_soc_pct,
    s.end_soc_pct,
    s.soc_delta_pct,
    s.energy_kwh,
    s.avg_charge_rate_kw,
    s.charger_type,
    s.is_fast_charge,
    s.ambient_temp_c
from {{ ref('int_charging_sessions_enriched') }} s
inner join {{ ref('dim_vehicles') }} v on s.vehicle_id = v.vehicle_id
