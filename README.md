# Jaipur Air Quality Analytics Portal

> A Python + SQL data engineering system that ingests CPCB historical air-quality observations for Jaipur, stores them in a relational database, and delivers an advanced analytics dashboard that tells you *what the data means* — not just what it shows.

---

## Problem Statement

Jaipur's air quality is monitored 24×7 by RSPCB stations under the CPCB CAAQM network.  
Raw 15-minute sensor readings are publicly available but buried in export files with no analytics layer on top.  
This project builds that layer: a full ETL pipeline + interactive reporting portal answering questions like:

- **When** is the worst time to step outside?
- **Does wind actually clean the air?**
- How many days exceeded the NAAQS PM2.5 standard in 2025?
- What is the seasonal pollution pattern across Jaipur?

---

## Architecture

```
CPCB-CCR Portal (Manual Export)
          │
          ▼
   data/raw/*.parquet          ← raw CPCB files
          │
          ▼
  src/extract/extract.py       ← column renaming, type coercion, NA handling
          │
          ▼
  src/transform/transform.py   ← outlier capping, AQI categorisation, insights
          │
          ▼
  src/load/load.py             ← schema init, station upsert, batch insert
          │
          ▼
  data/jaipur_aqi.db           ← SQLite (swap to SQL Server via .env)
  ┌──────────────┐
  │  stations    │
  │  measurements│
  │  daily_summary│
  └──────────────┘
          │
          ▼
    dashboard.py               ← Streamlit 4-page analytics portal
```

---

## Database Schema

| Table | Key Columns | Purpose |
|-------|-------------|---------|
| `stations` | station_id, station_name, city, state | Station lookup |
| `measurements` | station_id, ts, pm25, pm10, no2, so2, co, ozone, at, rh, ws… | Raw 15-min readings |
| `daily_summary` | station_id, summary_date, avg_pm25, aqi_category, dominant_poll | Pre-aggregated daily view |

Full schema: [`sql/01_create_schema.sql`](sql/01_create_schema.sql)  
Analysis queries: [`sql/02_analysis_queries.sql`](sql/02_analysis_queries.sql)

---

## Dataset

| Field | Value |
|-------|-------|
| Source | CPCB-CCR / RSPCB |
| Station | Shastri Nagar, Jaipur (site_1396) |
| Period | Jan 1 – Dec 31, 2025 |
| Granularity | 15 minutes |
| Rows | 35,040 |
| Pollutants | PM2.5, PM10, NO, NO2, NOx, NH3, SO2, CO, Ozone, Benzene, Toluene |
| Meteorology | AT, RH, WS, WD, RF, SR, BP |

---

## Setup

```bash
# 1. Clone / extract project
cd jaipur_aqi

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/Mac

# 3. Install dependencies
pip install -r requirements.txt

# 4. Place data file
#    Copy the CPCB parquet export to:
#    data/raw/Raw_data_15Min_2025_site_1396_Shastri_Nagar_Jaipur_RSPCB_15Min.parquet

# 5. Run pipeline (creates DB + loads all data)
python run_pipeline.py

# 6. Launch dashboard
streamlit run dashboard.py
```

### Using SQL Server instead of SQLite

Copy `.env.example` to `.env` and set:

```
DB_TYPE=mssql
MSSQL_SERVER=localhost\SQLEXPRESS
MSSQL_DB=JaipurAQI
```

Then run the pipeline as normal. The schema and all SQL is compatible with SQL Server with minor dialect differences handled by SQLAlchemy.

---

## Dashboard Pages

| Page | What it shows |
|------|---------------|
| 📊 Overview | Annual KPIs, AQI category distribution, monthly PM2.5 trend |
| 💡 What the Data Tells Us | Hourly patterns, wind-pollution relationship, weekday vs weekend, pollutant mix |
| 🔍 Advanced Search | Date/pollutant/aggregation filter → NAAQS check → export CSV |
| 🔬 Data Quality | Monthly availability heatmap, per-pollutant completeness stats |

---

## Key Findings (2025)

- **November was the worst month** — avg PM2.5 ~89.7 µg/m³ (49% above NAAQS)
- **August was the cleanest** — avg PM2.5 ~33.4 µg/m³ (monsoon washout effect)
- **10 PM–midnight** is consistently the worst window to be outdoors
- **4–5 AM** is paradoxically the cleanest time
- On calm days (wind < 1 m/s), PM2.5 is significantly higher than on windy days
- Data availability is ~95.6% for PM2.5 across the year

---

## SQL Analysis Queries

10 analysis queries covering:

1. Monthly PM2.5 seasonal trend  
2. Hour-of-day pollution profile  
3. Days exceeding NAAQS standard  
4. All-time worst readings  
5. PM2.5 vs NO2 correlation by hour  
6. Monthly data quality audit  
7. Wind speed vs PM2.5 relationship  
8. Weekend vs weekday comparison  
9. Rolling 7-day PM2.5 average  
10. AQI category distribution  

---

## Limitations

- Single station (Shastri Nagar) — multi-station comparison requires additional CPCB exports
- No real-time ingestion — manual export workflow
- SQLite used by default; SQL Server connection via `.env`

## Future Scope

- Multi-station comparison (Adarsh Nagar, Mansarovar, Police Commissionerate)
- Automated CPCB data ingestion via scheduled task
- Weather enrichment via OpenWeatherMap API
- AQI forecasting using time-series models
