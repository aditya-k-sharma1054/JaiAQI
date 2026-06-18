"""
extract.py — Load raw CPCB parquet/CSV export into a clean DataFrame.

Handles:
  - column renaming (unicode units stripped)
  - string "NA" → actual NaN
  - numeric coercion
  - basic row validation
"""
import pandas as pd
from pathlib import Path
from src.common.logger import get_logger

log = get_logger("extract")

COLUMN_MAP = {
    "Timestamp":           "ts",
    "PM2.5 (µg/m³)":      "pm25",
    "PM10 (µg/m³)":       "pm10",
    "NO (µg/m³)":         "no",
    "NO2 (µg/m³)":        "no2",
    "NOx (ppb)":          "nox",
    "NH3 (µg/m³)":        "nh3",
    "SO2 (µg/m³)":        "so2",
    "CO (mg/m³)":         "co",
    "Ozone (µg/m³)":      "ozone",
    "Benzene (µg/m³)":    "benzene",
    "Toluene (µg/m³)":    "toluene",
    "AT (°C)":            "at",
    "RH (%)":             "rh",
    "WS (m/s)":           "ws",
    "WD (deg)":           "wd",
    "RF (mm)":            "rf",
    "SR (W/mt2)":         "sr",
    "BP (mmHg)":          "bp",
}

NUMERIC_COLS = [c for c in COLUMN_MAP.values() if c != "ts"]


def load_file(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    log.info(f"Loading file: {path.name}")

    if path.suffix == ".parquet":
        df = pd.read_parquet(path)
    elif path.suffix in (".csv", ".xlsx"):
        df = pd.read_csv(path) if path.suffix == ".csv" else pd.read_excel(path)
    else:
        raise ValueError(f"Unsupported format: {path.suffix}")

    log.info(f"Raw shape: {df.shape}")
    return df


def extract(path: str | Path) -> pd.DataFrame:
    """Full extract → returns clean, typed DataFrame ready for transform."""
    df = load_file(path)

    # Keep only columns we know about
    known = {k: v for k, v in COLUMN_MAP.items() if k in df.columns}
    df = df[list(known.keys())].rename(columns=known)

    # Ensure timestamp is datetime
    df["ts"] = pd.to_datetime(df["ts"], errors="coerce")

    # Replace string "NA", "None", "---" with NaN
    df.replace(["NA", "None", "---", "", " "], pd.NA, inplace=True)

    # Coerce all measurement columns to float
    for col in NUMERIC_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop rows with no timestamp
    before = len(df)
    df.dropna(subset=["ts"], inplace=True)
    dropped = before - len(df)
    if dropped:
        log.warning(f"Dropped {dropped} rows with unparseable timestamps")

    # Sort chronologically
    df.sort_values("ts", inplace=True)
    df.reset_index(drop=True, inplace=True)

    log.info(f"Extracted {len(df):,} rows | "
             f"PM2.5 available: {df['pm25'].notna().sum():,} "
             f"({df['pm25'].notna().mean()*100:.1f}%)")
    return df


if __name__ == "__main__":
    import sys
    df = extract(sys.argv[1])
    print(df.describe())
