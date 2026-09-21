select
    region,
    count(*) as vehicle_count,
    round(avg(current_soh_pct), 2) as avg_soh_pct,
    round(min(current_soh_pct), 2) as min_soh_pct,
    sum(case when at_risk_soh_below_80 then 1 else 0 end) as at_risk_count,
    round(avg(degradation_pct_per_year), 3) as avg_degradation_pct_per_year
from {{ ref('mart_vehicle_battery_health') }}
group by region
order by avg_degradation_pct_per_year desc
