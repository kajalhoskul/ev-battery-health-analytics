select
    v.region,
    strftime(r.reading_date, '%Y-%m') as year_month,
    round(avg(r.state_of_health_pct), 2) as avg_soh_pct,
    count(distinct r.vehicle_id) as vehicle_count
from {{ ref('fact_battery_readings') }} r
inner join {{ ref('dim_vehicles') }} v on r.vehicle_id = v.vehicle_id
group by 1, 2
order by 1, 2
