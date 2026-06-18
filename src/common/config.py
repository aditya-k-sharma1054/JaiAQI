"""
config.py — Central configuration.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR  = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"

DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()

if DB_TYPE == "sqlite":
    DB_URL = f"sqlite:///{BASE_DIR / 'data' / 'jaipur_aqi.db'}"
else:
    server   = os.getenv("MSSQL_SERVER", r"localhost\SQLEXPRESS")
    database = os.getenv("MSSQL_DB",     "JaipurAQI")
    driver   = os.getenv("MSSQL_DRIVER", "ODBC Driver 17 for SQL Server")
    DB_URL = (
        f"mssql+pyodbc://@{server}/{database}"
        f"?driver={driver.replace(' ', '+')}&trusted_connection=yes"
    )

# Station registry — maps filename fragment → (display name, site_id)
STATIONS = {
    "site_134":  ("Police Commissionerate", "site_134"),
    "site_1393": ("Adarsh Nagar",           "site_1393"),
    "site_1396": ("Shastri Nagar",          "site_1396"),
    "site_5725": ("Mansarovar Sector-12",   "site_5725"),
    "site_5727": ("Murlipura Sector-2",     "site_5727"),
    "site_5728": ("RIICO Sitapura",         "site_5728"),
}

CITY  = "Jaipur"
STATE = "Rajasthan"

# NAAQS 24-hr standards
NAAQS = {
    "pm25":  60,
    "pm10":  100,
    "no2":   80,
    "so2":   80,
    "co":    2,
    "ozone": 100,
}

AQI_BINS   = [0, 30, 60, 90, 120, 250, float("inf")]
AQI_LABELS = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
