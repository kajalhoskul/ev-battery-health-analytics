"""Generates a synthetic EV fleet's battery telemetry and charging history,
with a realistic, explainable degradation model:

    SoH loss = calendar aging + cycle wear + fast-charging penalty + heat penalty

This mirrors the real, published finding (TWAICE, Geotab, and the broader
EV battery research this project is modeled on) that fast (DC) charging
and high ambient temperature measurably accelerate degradation beyond
simple calendar/cycle aging alone -- the fleet is deliberately generated
with varying regional climates and charging-habit mixes so that
relationship is genuinely present (and discoverable) in the data, not
just asserted.
"""
import csv
import math
import os
import random
from datetime import datetime, timedelta

MODELS = {
    "Ioniq5": 77.4,
    "Kona EV": 64.8,
    "Ioniq6": 77.4,
}

# (region, avg_ambient_c, is_hot)
REGIONS = [
    ("Phoenix-AZ", 32, True),
    ("Riyadh-SA", 34, True),
    ("Austin-TX", 26, False),
    ("Berlin-DE", 12, False),
    ("Seattle-WA", 14, False),
    ("Oslo-NO", 6, False),
]

N_VEHICLES = 150
FLEET_AGE_DAYS = 640  # ~21 months of history
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "raw")

CALENDAR_FADE_PER_YEAR = 1.6      # % SoH lost per year, calendar aging alone
CYCLE_FADE_PER_1000_CYCLES = 3.0  # % SoH lost per 1000 equivalent full cycles
FAST_CHARGE_PENALTY = 2.5         # extra % lost per year at 100% fast-charge usage
HEAT_PENALTY_PER_DEGREE_YEAR = 0.12  # extra % lost per year per degree C above 25


def simulate_vehicle(vehicle_id: int, rng: random.Random, today: datetime):
    model = rng.choice(list(MODELS.keys()))
    capacity_kwh = MODELS[model]
    region, avg_ambient, is_hot = rng.choice(REGIONS)

    manufacture_date = today - timedelta(days=rng.randint(200, FLEET_AGE_DAYS))
    daily_km = rng.uniform(20, 90)
    fast_charge_fraction = rng.betavariate(2, 5) if not is_hot else rng.betavariate(3, 3)
    # hot-climate owners skew toward more fast charging (road trips, less
    # home charging infrastructure in some of these markets) -- a
    # realistic confound the analytics should still be able to see through
    # since both regions have a spread of habits.

    vehicle = {
        "vehicle_id": vehicle_id,
        "model": model,
        "battery_capacity_kwh": capacity_kwh,
        "region": region,
        "manufacture_date": manufacture_date.date().isoformat(),
        "fast_charge_fraction": round(fast_charge_fraction, 3),
    }
    return vehicle, manufacture_date, daily_km, fast_charge_fraction, avg_ambient


def soh_at_age(age_years: float, cycles: float, fast_charge_fraction: float, avg_ambient: float, rng: random.Random) -> float:
    calendar_loss = CALENDAR_FADE_PER_YEAR * age_years
    cycle_loss = CYCLE_FADE_PER_1000_CYCLES * (cycles / 1000)
    fast_charge_loss = FAST_CHARGE_PENALTY * fast_charge_fraction * age_years
    heat_loss = HEAT_PENALTY_PER_DEGREE_YEAR * max(0, avg_ambient - 25) * age_years
    noise = rng.uniform(-0.4, 0.4)
    soh = 100 - calendar_loss - cycle_loss - fast_charge_loss - heat_loss + noise
    return max(60.0, min(100.0, soh))


def main():
    rng = random.Random(42)
    today = datetime.now()

    vehicles = []
    readings = []
    sessions = []
    charge_id = 1

    for vehicle_id in range(1, N_VEHICLES + 1):
        vehicle, manufacture_date, daily_km, fast_charge_fraction, avg_ambient = simulate_vehicle(vehicle_id, rng, today)
        vehicles.append(vehicle)

        capacity_kwh = vehicle["battery_capacity_kwh"]
        km_per_full_cycle = 350  # ~ full pack-equivalent range per cycle
        day = manufacture_date
        cumulative_km = 0.0

        while day <= today:
            age_years = (day - manufacture_date).days / 365.25
            daily_km_actual = max(0, rng.gauss(daily_km, daily_km * 0.3))
            cumulative_km += daily_km_actual
            cycles = cumulative_km / km_per_full_cycle

            if day.day % 3 == 0:  # snapshot every ~3 days, not literally daily
                soh = soh_at_age(age_years, cycles, fast_charge_fraction, avg_ambient, rng)
                readings.append({
                    "vehicle_id": vehicle_id,
                    "reading_date": day.date().isoformat(),
                    "odometer_km": round(cumulative_km, 1),
                    "cycle_count": round(cycles, 2),
                    "state_of_health_pct": round(soh, 2),
                    "pack_temperature_avg_c": round(avg_ambient + rng.uniform(-3, 3), 1),
                })

            # ~1 charging session every 2-3 days
            if rng.random() < 0.4:
                is_fast = rng.random() < fast_charge_fraction
                start_soc = rng.uniform(15, 60)
                end_soc = min(100, start_soc + rng.uniform(20, 60))
                energy_kwh = (end_soc - start_soc) / 100 * capacity_kwh
                duration_min = energy_kwh / (rng.uniform(40, 60) if is_fast else rng.uniform(6, 11)) * 60
                sessions.append({
                    "charge_id": charge_id,
                    "vehicle_id": vehicle_id,
                    "start_time": day.isoformat(timespec="minutes"),
                    "end_time": (day + timedelta(minutes=duration_min)).isoformat(timespec="minutes"),
                    "start_soc_pct": round(start_soc, 1),
                    "end_soc_pct": round(end_soc, 1),
                    "energy_kwh": round(energy_kwh, 2),
                    "charger_type": "DC_FAST" if is_fast else "AC_L2",
                    "ambient_temp_c": round(avg_ambient + rng.uniform(-4, 4), 1),
                })
                charge_id += 1

            day += timedelta(days=1)

    os.makedirs(OUT_DIR, exist_ok=True)
    write_csv(os.path.join(OUT_DIR, "vehicles.csv"), vehicles)
    write_csv(os.path.join(OUT_DIR, "battery_readings.csv"), readings)
    write_csv(os.path.join(OUT_DIR, "charging_sessions.csv"), sessions)
    print(f"Wrote {len(vehicles)} vehicles, {len(readings)} battery readings, "
          f"{len(sessions)} charging sessions -> {OUT_DIR}")


def write_csv(path, rows):
    if not rows:
        return
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    main()
