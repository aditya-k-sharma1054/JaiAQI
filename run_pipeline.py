import sys, re, time, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.extract.extract import extract
from src.transform.transform import clean_measurements, build_daily_summary, compute_insights
from src.load.load import get_engine, init_schema, upsert_station, load_measurements, load_daily_summary
from src.common.logger import get_logger
from src.common.config import DATA_DIR, STATIONS

log = get_logger("pipeline")


def station_from_filename(path: Path):
    """Return (display_name, site_id) by matching filename against STATIONS registry."""
    name = path.stem
    for key, (display, site_id) in STATIONS.items():
        if key in name:
            return display, site_id
    # Fallback: parse from filename
    m = re.search(r'(site_\d+)', name)
    site_id = m.group(1) if m else "unknown"
    # Humanise the rest
    display = name.split(site_id + "_")[-1].replace("_Jaipur", "").replace("_", " ").strip()
    return display, site_id


def process_file(path: Path, engine):
    log.info(f"--- Processing: {path.name}")
    station_name, site_id = station_from_filename(path)
    log.info(f"    Station: {station_name} ({site_id})")

    df_raw   = extract(path)
    sid      = upsert_station(station_name, site_id, engine)
    df_clean = clean_measurements(df_raw, sid)
    load_measurements(df_clean, engine)
    df_daily = build_daily_summary(df_clean, sid)
    load_daily_summary(df_daily, engine)
    return df_clean, station_name


def run(target=None):
    t0 = time.time()

    if target:
        files = [Path(target)]
    else:
        raw_dir = DATA_DIR / "raw"
        files   = sorted(raw_dir.glob("*.parquet"))
        if not files:
            log.error(f"No parquet files found in {raw_dir}")
            sys.exit(1)

    log.info("=" * 60)
    log.info(f"JAIPUR AQI PIPELINE — {len(files)} file(s)")
    log.info("=" * 60)

    engine = get_engine()
    init_schema(engine)

    all_dfs = []
    for f in files:
        df_clean, name = process_file(f, engine)
        all_dfs.append(df_clean)

    # Combined insights across all stations
    import pandas as pd
    df_all = pd.concat(all_dfs, ignore_index=True)
    insights = compute_insights(df_all)
    (DATA_DIR / "processed").mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "processed" / "insights.json").write_text(json.dumps(insights, indent=2))

    elapsed = round(time.time() - t0, 1)
    total_rows = sum(len(d) for d in all_dfs)
    log.info("=" * 60)
    log.info(f"PIPELINE COMPLETE in {elapsed}s")
    log.info(f"  Stations processed : {len(files)}")
    log.info(f"  Total rows         : {total_rows:,}")
    log.info(f"  Database           : {engine.url}")
    log.info("=" * 60)


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else None)
