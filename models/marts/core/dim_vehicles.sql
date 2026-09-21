select
    vehicle_id as vehicle_sk,
    vehicle_id,
    model,
    battery_capacity_kwh,
    region,
    manufacture_date,
    fast_charge_fraction,
    date_diff('day', manufacture_date, current_date) as age_days
from {{ ref('stg_vehicles') }}
