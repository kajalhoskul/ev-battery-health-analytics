#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

echo "== 1/5  Generating fleet telemetry =="
python3 data_generation/generate_fleet_data.py

echo "== 2/5  Loading raw data into DuckDB =="
python3 data_generation/load_raw.py

echo "== 3/5  Running all dbt models =="
dbt run --profiles-dir .

echo "== 4/5  Running dbt tests =="
dbt test --profiles-dir .

echo "== 5/5  Building the dashboard =="
python3 dashboard/build_dashboard.py

echo
echo "Done. Open dashboard/dashboard.html in a browser to view the results."
