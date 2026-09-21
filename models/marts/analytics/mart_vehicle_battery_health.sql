-- One row per vehicle: current SoH, its own fitted degradation trend
-- (linear regression of SoH% against age in days across all its
-- readings), and a remaining-useful-life projection to a 70% SoH
-- end-of-life threshold -- the standard EV industry definition of
-- "battery replacement warranty" territory.

with readings as (
    select * from {{ ref('fact_battery_readings') }}
),

per_vehicle_trend as (
    select
        vehicle_id,
        regr_slope(state_of_health_pct, age_days) as slope_pct_per_day,
        regr_intercept(state_of_health_pct, age_days) as intercept_pct,
        max(age_days) as current_age_days,
        count(*) as reading_count
    from readings
    group by vehicle_id
    having count(*) >= 5
),

current_soh as (
    select vehicle_id, state_of_health_pct as current_soh_pct, cycle_count, odometer_km
    from readings
    qualify row_number() over (partition by vehicle_id order by reading_date desc) = 1
)

select
    v.vehicle_id,
    v.model,
    v.region,
    v.battery_capacity_kwh,
    v.fast_charge_fraction,
    v.age_days,
    c.current_soh_pct,
    c.cycle_count,
    c.odometer_km,
    t.slope_pct_per_day,
    round(t.slope_pct_per_day * 365, 3) as degradation_pct_per_year,
    case
        when t.slope_pct_per_day < -0.0001
            then greatest(0, round((70 - t.intercept_pct) / t.slope_pct_per_day - t.current_age_days))
        else null
    end as projected_days_to_70pct_soh,
    c.current_soh_pct < 80 as at_risk_soh_below_80
from {{ ref('dim_vehicles') }} v
inner join current_soh c on v.vehicle_id = c.vehicle_id
inner join per_vehicle_trend t on v.vehicle_id = t.vehicle_id
