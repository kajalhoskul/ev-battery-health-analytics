-- Isolates the two behavioral/climate drivers this project's data
-- generator actually encodes (fast-charging habit and ambient
-- temperature), by bucketing vehicles into fast-charge-usage terciles
-- within each climate group, and comparing average degradation rate.
-- If the fleet were generated with no such effect, these buckets would
-- show flat degradation rates; the point is to demonstrate the analytics
-- actually recovering a real, known relationship from raw telemetry.

with climate as (
    select
        vehicle_id,
        region,
        case
            when region in ('Phoenix-AZ', 'Riyadh-SA') then 'Hot'
            when region in ('Austin-TX') then 'Moderate'
            else 'Mild'
        end as climate_zone
    from {{ ref('dim_vehicles') }}
),

bucketed as (
    select
        h.vehicle_id,
        c.climate_zone,
        h.fast_charge_fraction,
        h.degradation_pct_per_year,
        ntile(3) over (order by h.fast_charge_fraction) as fast_charge_tercile
    from {{ ref('mart_vehicle_battery_health') }} h
    inner join climate c on h.vehicle_id = c.vehicle_id
)

select
    climate_zone,
    case fast_charge_tercile
        when 1 then 'Low fast-charge usage'
        when 2 then 'Medium fast-charge usage'
        when 3 then 'High fast-charge usage'
    end as fast_charge_usage_group,
    count(*) as vehicle_count,
    round(avg(fast_charge_fraction), 2) as avg_fast_charge_fraction,
    round(avg(degradation_pct_per_year), 3) as avg_degradation_pct_per_year
from bucketed
group by climate_zone, fast_charge_tercile
order by climate_zone, fast_charge_tercile
