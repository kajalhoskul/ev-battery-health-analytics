# EV Battery Health Analytics

A dbt + DuckDB analytics warehouse for a 150-vehicle EV fleet's battery
telemetry: state-of-health tracking, remaining-useful-life projection, and
-- the actual point of the project -- **recovering the real, published
relationship between fast-charging habits, climate, and battery
degradation directly from raw telemetry**, the way OEM fleet-analytics
platforms (Geotab, TWAICE) actually do this.

## Why this matters

OEMs including Hyundai are investing heavily in EV predictive-maintenance
platforms; Geotab alone processes 40 billion telemetry points a day across
2M+ connected vehicles for exactly this kind of analysis. The two levers
research consistently identifies as accelerating degradation beyond normal
calendar/cycle aging are **DC fast-charging frequency** and **high ambient
temperature**. This project's synthetic fleet is generated with both
effects genuinely built into the underlying physics (see
`data_generation/generate_fleet_data.py`), then the dbt marts independently
recover that relationship from the raw per-vehicle telemetry using linear
regression -- nothing about the effect is hardcoded into the analytics
layer itself.

## Architecture

```
data/raw/*.csv                    (150 vehicles, ~22k battery readings, ~27k charging sessions)
        |
        v   data_generation/load_raw.py
   raw.*  (DuckDB tables)
        |
        v   dbt models/staging
   stg_vehicles, stg_battery_readings, stg_charging_sessions
        |
        v   dbt models/intermediate
   int_charging_sessions_enriched   (session duration, avg charge rate, is_fast_charge)
        |
        v   dbt models/marts/core
   dim_vehicles   fact_battery_readings   fact_charging_sessions
        |
        v   dbt models/marts/analytics
   mart_vehicle_battery_health   (per-vehicle SoH trend + RUL, via regr_slope/regr_intercept)
   mart_fleet_health_summary     (by region)
   mart_degradation_drivers      (fast-charge tercile x climate zone)
   mart_soh_trend_monthly        (fleet SoH trend line by region)
        |
        v   dashboard/build_dashboard.py
   dashboard/dashboard.html
```

### How the remaining-useful-life projection works

`mart_vehicle_battery_health` fits a per-vehicle linear trend of SoH% vs.
age-in-days using DuckDB's `regr_slope`/`regr_intercept` aggregate
functions across that vehicle's full reading history, then projects
forward to the age at which SoH would cross 70% -- the industry-standard
EV battery warranty end-of-life threshold -- and reports the remaining
days from today. A vehicle with too few readings (<5) or a non-degrading
fitted trend is excluded rather than given a nonsensical projection.

## Setup

```bash
pip install -r requirements.txt
```

## Running everything

```bash
./run_pipeline.sh
```

Or step by step:

```bash
python3 data_generation/generate_fleet_data.py   # generate data/raw/*.csv
python3 data_generation/load_raw.py              # load into warehouse.duckdb (raw schema)
dbt run --profiles-dir .                         # build staging -> intermediate -> marts
dbt test --profiles-dir .                        # run all 24 data quality tests
python3 dashboard/build_dashboard.py             # build dashboard/dashboard.html
```

## Project layout

```
data_generation/        fleet + telemetry generator, raw loader
data/raw/                generated vehicles/readings/sessions extracts
models/staging/          typed/cleaned views over each raw source
models/intermediate/     charging-session enrichment (duration, charge rate)
models/marts/core/       dim_vehicles, fact_battery_readings, fact_charging_sessions
models/marts/analytics/  SoH trend, fleet health summary, degradation drivers, RUL
dashboard/               Plotly dashboard builder + output HTML
```
