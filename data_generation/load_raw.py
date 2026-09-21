"""Loads the raw fleet CSVs into the `raw` schema of the DuckDB warehouse
file, the ELT extract-and-load step dbt then transforms.

Usage:
    python load_raw.py
"""
import os

import duckdb

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DB_PATH = os.path.join(BASE_DIR, "warehouse.duckdb")
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")

TABLES = ["vehicles", "battery_readings", "charging_sessions"]


def main():
    con = duckdb.connect(DB_PATH)
    con.execute("CREATE SCHEMA IF NOT EXISTS raw")
    for table in TABLES:
        csv_path = os.path.join(RAW_DIR, f"{table}.csv")
        con.execute(f"""
            CREATE OR REPLACE TABLE raw.{table} AS
            SELECT * FROM read_csv_auto('{csv_path}', header=True)
        """)
        count = con.execute(f"SELECT count(*) FROM raw.{table}").fetchone()[0]
        print(f"Loaded raw.{table}: {count} rows")
    con.close()


if __name__ == "__main__":
    main()
