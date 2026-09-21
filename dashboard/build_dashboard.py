"""Builds a single self-contained HTML analytics dashboard by querying the
dbt marts directly out of the DuckDB warehouse file.

Usage:
    python build_dashboard.py
"""
import os

import duckdb
import plotly.graph_objects as go
from plotly.offline import plot

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
DB_PATH = os.path.join(BASE_DIR, "warehouse.duckdb")
OUT_PATH = os.path.join(os.path.dirname(__file__), "dashboard.html")

# Colors from the validated reference palette: fixed categorical order,
# sequential blue ramp for magnitude.
INK_PRIMARY = "#0b0b0b"
INK_SECONDARY = "#52514e"
INK_MUTED = "#898781"
GRIDLINE = "#e1e0d9"
SURFACE = "#fcfcfb"
CATEGORICAL = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#4a3aa7"]  # blue, orange, aqua, yellow, magenta, violet
SEQUENTIAL_BLUE = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#1c5cab", "#0d366b"]

BASE_LAYOUT = dict(
    paper_bgcolor=SURFACE,
    plot_bgcolor=SURFACE,
    font=dict(family="system-ui, -apple-system, Segoe UI, sans-serif", color=INK_PRIMARY, size=13),
    margin=dict(l=60, r=30, t=60, b=50),
    hoverlabel=dict(bgcolor="white", font_size=12),
)
AXIS_STYLE = dict(
    gridcolor=GRIDLINE,
    zerolinecolor=GRIDLINE,
    linecolor=INK_MUTED,
    tickfont=dict(color=INK_SECONDARY),
)


def fig_soh_trend_by_region(con):
    rows = con.execute("""
        select region, year_month, avg_soh_pct
        from main_analytics.mart_soh_trend_monthly
        order by region, year_month
    """).fetchall()

    by_region = {}
    for region, month, soh in rows:
        by_region.setdefault(region, {"x": [], "y": []})
        by_region[region]["x"].append(month)
        by_region[region]["y"].append(soh)

    fig = go.Figure()
    for i, (region, series) in enumerate(sorted(by_region.items())):
        color = CATEGORICAL[i % len(CATEGORICAL)]
        fig.add_trace(go.Scatter(
            x=series["x"], y=series["y"], mode="lines", name=region,
            line=dict(color=color, width=2),
            hovertemplate="%{x}<br>" + region + ": %{y:.1f}%<extra></extra>",
        ))
    fig.update_layout(
        **BASE_LAYOUT,
        title="Average Battery State of Health by Region",
        xaxis=dict(title=None, **AXIS_STYLE),
        yaxis=dict(title="Avg SoH (%)", **AXIS_STYLE),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hovermode="x unified",
        height=380,
    )
    return fig


def fig_degradation_by_region(con):
    rows = con.execute("""
        select region, avg_degradation_pct_per_year
        from main_analytics.mart_fleet_health_summary
        order by avg_degradation_pct_per_year asc
    """).fetchall()
    regions = [r[0] for r in rows]
    rates = [abs(r[1]) for r in rows]

    fig = go.Figure(go.Bar(
        x=regions, y=rates,
        marker=dict(color=CATEGORICAL[0]),
        text=[f"{r:.2f}%" for r in rates], textposition="outside",
        hovertemplate="%{x}: %{y:.2f}%/year<extra></extra>",
    ))
    fig.update_layout(
        **BASE_LAYOUT,
        title="Fleet Degradation Rate by Region (SoH lost per year)",
        xaxis=dict(title=None, **AXIS_STYLE),
        yaxis=dict(title="SoH lost (% / year)", **AXIS_STYLE),
        showlegend=False,
        height=400,
    )
    return fig


def fig_degradation_drivers(con):
    rows = con.execute("""
        select climate_zone, fast_charge_usage_group, avg_degradation_pct_per_year
        from main_analytics.mart_degradation_drivers
        order by climate_zone, fast_charge_usage_group
    """).fetchall()

    usage_order = ["Low fast-charge usage", "Medium fast-charge usage", "High fast-charge usage"]
    by_climate = {}
    for climate, usage, rate in rows:
        by_climate.setdefault(climate, {u: None for u in usage_order})
        by_climate[climate][usage] = abs(rate)

    fig = go.Figure()
    climate_order = ["Mild", "Moderate", "Hot"]
    for i, climate in enumerate(climate_order):
        if climate not in by_climate:
            continue
        color = CATEGORICAL[i % len(CATEGORICAL)]
        y = [by_climate[climate][u] for u in usage_order]
        fig.add_trace(go.Bar(
            x=usage_order, y=y, name=climate,
            marker=dict(color=color),
            hovertemplate="%{x}<br>" + climate + ": %{y:.2f}%/year<extra></extra>",
        ))
    fig.update_layout(
        **BASE_LAYOUT,
        title="Degradation Rate by Fast-Charging Habit and Climate",
        xaxis=dict(title=None, **AXIS_STYLE),
        yaxis=dict(title="SoH lost (% / year)", **AXIS_STYLE),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        barmode="group",
        height=420,
    )
    return fig


def fig_rul_distribution(con):
    rows = con.execute("""
        select projected_days_to_70pct_soh
        from main_analytics.mart_vehicle_battery_health
        where projected_days_to_70pct_soh is not null
    """).fetchall()
    values = [r[0] / 365.0 for r in rows]

    fig = go.Figure(go.Histogram(
        x=values,
        marker=dict(color=SEQUENTIAL_BLUE[3]),
        nbinsx=20,
        hovertemplate="%{x:.1f} years<br>%{y} vehicles<extra></extra>",
    ))
    fig.update_layout(
        **BASE_LAYOUT,
        title="Projected Years Until 70% SoH (Battery Warranty Threshold)",
        xaxis=dict(title="Years from today", **AXIS_STYLE),
        yaxis=dict(title="Vehicles", **AXIS_STYLE),
        showlegend=False,
        height=380,
    )
    return fig


def main():
    con = duckdb.connect(DB_PATH, read_only=True)

    figures = [
        fig_soh_trend_by_region(con),
        fig_degradation_by_region(con),
        fig_degradation_drivers(con),
        fig_rul_distribution(con),
    ]
    con.close()

    divs = []
    for i, fig in enumerate(figures):
        divs.append(plot(fig, include_plotlyjs=(i == 0), output_type="div"))

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>EV Fleet Battery Health Dashboard</title>
<style>
  body {{
    background: #f9f9f7;
    font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
    color: {INK_PRIMARY};
    margin: 0;
    padding: 32px;
  }}
  h1 {{ font-size: 22px; margin-bottom: 4px; }}
  p.subtitle {{ color: {INK_SECONDARY}; margin-top: 0; margin-bottom: 28px; }}
  .card {{
    background: {SURFACE};
    border: 1px solid rgba(11,11,11,0.10);
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 24px;
    max-width: 1000px;
  }}
</style>
</head>
<body>
  <h1>EV Fleet Battery Health Dashboard</h1>
  <p class="subtitle">Generated from the ev_battery_warehouse dbt marts (DuckDB) -- 150 vehicles.</p>
  <div class="card">{divs[0]}</div>
  <div class="card">{divs[1]}</div>
  <div class="card">{divs[2]}</div>
  <div class="card">{divs[3]}</div>
</body>
</html>
"""

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Wrote dashboard -> {OUT_PATH}")


if __name__ == "__main__":
    main()
