"""
transform.py — Clean, enrich, and derive features from raw measurements.

Key outputs:
  - cleaned measurements DataFrame (station_id column added)
  - daily_summary DataFrame
"""
import pandas as pd
import numpy as np
from src.common.config import AQI_BINS, AQI_LABELS, NAAQS
from src.common.logger import get_logger

log = get_logger("transform")


# ---------------------------------------------------------------------------
# AQI helpers
# ---------------------------------------------------------------------------

def _pm25_to_aqi_category(pm25_24hr: float) -> str:
    """Map 24-hr avg PM2.5 to India AQI category."""
    if pd.isna(pm25_24hr):
        return None
    for lo, hi, label in zip(AQI_BINS, AQI_BINS[1:], AQI_LABELS):
        if lo <= pm25_24hr < hi:
            return label
    return "Severe"


def _dominant_pollutant(row: pd.Series) -> str:
    """Return the pollutant with highest NAAQS exceedance ratio."""
    ratios = {}
    mapping = {
        "pm25": ("avg_pm25", NAAQS["pm25"]),
        "pm10": ("avg_pm10", NAAQS["pm10"]),
        "no2":  ("avg_no2",  NAAQS["no2"]),
        "so2":  ("avg_so2",  NAAQS["so2"]),
    }
    for poll, (col, std) in mapping.items():
        val = row.get(col)
        if pd.notna(val) and std > 0:
            ratios[poll] = val / std
    if not ratios:
        return None
    return max(ratios, key=ratios.get).upper()


# ---------------------------------------------------------------------------
# Main transforms
# ---------------------------------------------------------------------------

def clean_measurements(df: pd.DataFrame, station_id: int) -> pd.DataFrame:
    """Add station_id; cap extreme outliers; return copy."""
    df = df.copy()
    df["station_id"] = station_id

    # Cap physical impossibilities
    caps = {"pm25": 1500, "pm10": 2000, "no2": 500, "so2": 500,
            "co": 50, "ozone": 600, "at": 60, "rh": 100}
    floors = {"pm25": 0, "pm10": 0, "no2": 0, "so2": 0, "co": 0,
              "ozone": 0, "at": -10, "rh": 0}
    for col, cap in caps.items():
        if col in df:
            before = df[col].notna().sum()
            df[col] = df[col].clip(lower=floors.get(col, None), upper=cap)
    
    # Derived: AQI category per row (using PM2.5 as proxy)
    df["aqi_category"] = df["pm25"].apply(_pm25_to_aqi_category)

    log.info(f"Cleaned measurements: {len(df):,} rows, station_id={station_id}")
    return df


def build_daily_summary(df: pd.DataFrame, station_id: int) -> pd.DataFrame:
    """Aggregate 15-min data → daily summary rows."""
    df = df.copy()
    df["date"] = df["ts"].dt.date

    agg = df.groupby("date").agg(
        avg_pm25=("pm25",  "mean"),
        max_pm25=("pm25",  "max"),
        avg_pm10=("pm10",  "mean"),
        avg_no2 =("no2",   "mean"),
        avg_so2 =("so2",   "mean"),
        avg_co  =("co",    "mean"),
        avg_ozone=("ozone","mean"),
        readings_count=("pm25", "count"),
    ).reset_index()

    agg.rename(columns={"date": "summary_date"}, inplace=True)
    agg["station_id"]    = station_id
    agg["aqi_category"]  = agg["avg_pm25"].apply(_pm25_to_aqi_category)
    agg["dominant_poll"] = agg.apply(_dominant_pollutant, axis=1)

    # Round numerics
    num_cols = [c for c in agg.columns if agg[c].dtype == float]
    agg[num_cols] = agg[num_cols].round(2)

    log.info(f"Built {len(agg):,} daily summary rows")
    return agg


def compute_insights(df: pd.DataFrame) -> dict:
    """
    Return a dict of pre-computed insight strings for the dashboard.
    These power the 'Story' section — telling not just displaying.
    """
    df = df.copy()
    df["month"] = df["ts"].dt.month
    df["hour"]  = df["ts"].dt.hour
    df["dow"]   = df["ts"].dt.dayofweek   # 0=Mon

    insights = {}

    # Worst month
    monthly = df.groupby("month")["pm25"].mean()
    worst_m = monthly.idxmax()
    month_names = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                   7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
    insights["worst_month"] = month_names[worst_m]
    insights["worst_month_pm25"] = round(monthly[worst_m], 1)

    # Best month
    best_m = monthly.idxmin()
    insights["best_month"] = month_names[best_m]
    insights["best_month_pm25"] = round(monthly[best_m], 1)

    # Worst hour
    hourly = df.groupby("hour")["pm25"].mean()
    worst_h = hourly.idxmax()
    insights["worst_hour"] = f"{worst_h:02d}:00"
    insights["worst_hour_pm25"] = round(hourly[worst_h], 1)

    # Best hour
    best_h = hourly.idxmin()
    insights["best_hour"] = f"{best_h:02d}:00"
    insights["best_hour_pm25"] = round(hourly[best_h], 1)

    # Weekday vs weekend
    df["is_weekend"] = df["dow"].isin([5, 6])
    wk = df.groupby("is_weekend")["pm25"].mean()
    insights["weekday_pm25"]  = round(wk.get(False, float("nan")), 1)
    insights["weekend_pm25"]  = round(wk.get(True,  float("nan")), 1)

    # NAAQS exceedance days
    daily_avg = df.groupby(df["ts"].dt.date)["pm25"].mean()
    exceed = (daily_avg > NAAQS["pm25"]).sum()
    insights["naaqs_exceed_days"] = int(exceed)
    insights["naaqs_exceed_pct"]  = round(100 * exceed / max(len(daily_avg), 1), 1)

    # Wind-pollution correlation narrative
    calm  = df[df["ws"] < 1]["pm25"].mean() if "ws" in df.columns else None
    windy = df[df["ws"] >= 3]["pm25"].mean() if "ws" in df.columns else None
    if calm and windy:
        insights["calm_pm25"]  = round(calm, 1)
        insights["windy_pm25"] = round(windy, 1)
        insights["wind_lift"]  = round(calm - windy, 1)

    log.info("Computed insights: %s", list(insights.keys()))
    return insights
