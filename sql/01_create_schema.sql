-- Jaipur Air Quality Analytics - Schema
-- Compatible with: SQL Server / SQLite

-- Stations lookup
CREATE TABLE IF NOT EXISTS stations (
    station_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    station_name TEXT NOT NULL UNIQUE,
    city         TEXT NOT NULL DEFAULT 'Jaipur',
    state        TEXT NOT NULL DEFAULT 'Rajasthan',
    source_site  TEXT,
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Raw 15-min measurements (one row per reading interval)
CREATE TABLE IF NOT EXISTS measurements (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id   INTEGER NOT NULL REFERENCES stations(station_id),
    ts           DATETIME NOT NULL,
    pm25         REAL,
    pm10         REAL,
    no           REAL,
    no2          REAL,
    nox          REAL,
    nh3          REAL,
    so2          REAL,
    co           REAL,
    ozone        REAL,
    benzene      REAL,
    toluene      REAL,
    at           REAL,
    rh           REAL,
    ws           REAL,
    wd           REAL,
    rf           REAL,
    sr           REAL,
    bp           REAL,
    inserted_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(station_id, ts)
);

-- Daily summaries per station (pre-computed for speed)
CREATE TABLE IF NOT EXISTS daily_summary (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    station_id       INTEGER NOT NULL REFERENCES stations(station_id),
    summary_date     DATE NOT NULL,
    avg_pm25         REAL,
    max_pm25         REAL,
    avg_pm10         REAL,
    avg_no2          REAL,
    avg_so2          REAL,
    avg_co           REAL,
    avg_ozone        REAL,
    aqi_category     TEXT,
    dominant_poll    TEXT,
    readings_count   INTEGER,
    UNIQUE(station_id, summary_date)
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_meas_ts         ON measurements(ts);
CREATE INDEX IF NOT EXISTS idx_meas_station_ts ON measurements(station_id, ts);
CREATE INDEX IF NOT EXISTS idx_daily_date      ON daily_summary(summary_date);
