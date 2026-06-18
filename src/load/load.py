"""
load.py — Push cleaned DataFrames into SQLite (or SQL Server).
Supports multiple stations.
"""
from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text
from src.common.config import DB_URL, CITY, STATE
from src.common.logger import get_logger

log = get_logger("load")


def get_engine():
    return create_engine(DB_URL, echo=False)


def init_schema(engine=None):
    engine = engine or get_engine()
    schema_path = Path(__file__).parents[2] / "sql" / "01_create_schema.sql"
    sql = schema_path.read_text()
    with engine.connect() as conn:
        for stmt in sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
        conn.commit()
    log.info("Schema initialised")


def upsert_station(station_name: str, site_id: str, engine=None) -> int:
    """Insert or get station by name, return station_id."""
    engine = engine or get_engine()
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT station_id FROM stations WHERE station_name = :name"),
            {"name": station_name}
        ).fetchone()
        if row:
            return row[0]
        conn.execute(
            text("""INSERT INTO stations (station_name, city, state, source_site)
                    VALUES (:name, :city, :state, :site)"""),
            {"name": station_name, "city": CITY, "state": STATE, "site": site_id}
        )
        conn.commit()
        sid = conn.execute(
            text("SELECT station_id FROM stations WHERE station_name = :name"),
            {"name": station_name}
        ).fetchone()[0]
        log.info(f"Inserted station '{station_name}' → id={sid}")
        return sid


def load_measurements(df: pd.DataFrame, engine=None, batch_size: int = 2000):
    engine = engine or get_engine()
    cols = ["station_id", "ts", "pm25", "pm10", "no", "no2", "nox",
            "nh3", "so2", "co", "ozone", "benzene", "toluene",
            "at", "rh", "ws", "wd", "rf", "sr", "bp"]
    cols = [c for c in cols if c in df.columns]
    chunk = df[cols].copy()
    chunk["ts"] = chunk["ts"].astype(str)

    inserted = skipped = 0
    for i in range(0, len(chunk), batch_size):
        batch = chunk.iloc[i: i + batch_size]
        try:
            batch.to_sql("measurements", engine, if_exists="append",
                         index=False, method="multi")
            inserted += len(batch)
        except Exception:
            for _, row in batch.iterrows():
                try:
                    pd.DataFrame([row]).to_sql("measurements", engine,
                                               if_exists="append", index=False)
                    inserted += 1
                except Exception:
                    skipped += 1

    log.info(f"  Measurements: inserted={inserted:,}, skipped(dup)={skipped:,}")


def load_daily_summary(df: pd.DataFrame, engine=None):
    engine = engine or get_engine()
    df = df.copy()
    df["summary_date"] = df["summary_date"].astype(str)
    inserted = skipped = 0
    for _, row in df.iterrows():
        try:
            pd.DataFrame([row]).to_sql("daily_summary", engine,
                                       if_exists="append", index=False)
            inserted += 1
        except Exception:
            skipped += 1
    log.info(f"  Daily summary: inserted={inserted:,}, skipped(dup)={skipped:,}")
