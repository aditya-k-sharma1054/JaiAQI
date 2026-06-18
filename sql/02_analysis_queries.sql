-- Jaipur AQI Analytics - 10 Analysis Queries
-- Run against: measurements + daily_summary tables

-- Q1: Monthly average PM2.5 trend (seasonal pollution pattern)
SELECT
    strftime('%Y-%m', ts) AS month,
    ROUND(AVG(pm25), 2)   AS avg_pm25,
    ROUND(MAX(pm25), 2)   AS peak_pm25,
    COUNT(*)              AS readings
FROM measurements
WHERE pm25 IS NOT NULL
GROUP BY strftime('%Y-%m', ts)
ORDER BY month;

-- Q2: Hour-of-day pollution pattern (when is Jaipur worst?)
SELECT
    CAST(strftime('%H', ts) AS INTEGER) AS hour_of_day,
    ROUND(AVG(pm25), 2)  AS avg_pm25,
    ROUND(AVG(pm10), 2)  AS avg_pm10,
    ROUND(AVG(no2), 2)   AS avg_no2
FROM measurements
WHERE pm25 IS NOT NULL
GROUP BY hour_of_day
ORDER BY hour_of_day;

-- Q3: Days exceeding NAAQS PM2.5 standard (60 µg/m³ 24hr avg)
SELECT
    summary_date,
    ROUND(avg_pm25, 2) AS daily_avg_pm25,
    aqi_category
FROM daily_summary
WHERE avg_pm25 > 60
ORDER BY avg_pm25 DESC
LIMIT 30;

-- Q4: Worst 10 single readings ever recorded
SELECT
    ts,
    pm25, pm10, no2, so2, co, ozone
FROM measurements
WHERE pm25 IS NOT NULL
ORDER BY pm25 DESC
LIMIT 10;

-- Q5: Pollutant correlation check (PM2.5 vs NO2)
SELECT
    ROUND(AVG(pm25), 2) AS avg_pm25,
    ROUND(AVG(no2), 2)  AS avg_no2,
    strftime('%H', ts)  AS hour
FROM measurements
WHERE pm25 IS NOT NULL AND no2 IS NOT NULL
GROUP BY hour
ORDER BY hour;

-- Q6: Data quality audit (missing readings per month)
SELECT
    strftime('%Y-%m', ts)                           AS month,
    COUNT(*)                                        AS total_slots,
    SUM(CASE WHEN pm25 IS NULL THEN 1 ELSE 0 END)  AS missing_pm25,
    SUM(CASE WHEN pm10 IS NULL THEN 1 ELSE 0 END)  AS missing_pm10,
    ROUND(
        100.0 * SUM(CASE WHEN pm25 IS NOT NULL THEN 1 ELSE 0 END) / COUNT(*), 1
    )                                               AS pm25_availability_pct
FROM measurements
GROUP BY strftime('%Y-%m', ts)
ORDER BY month;

-- Q7: Wind speed vs PM2.5 relationship (pollution trapping)
SELECT
    CASE
        WHEN ws < 1  THEN 'Calm (<1 m/s)'
        WHEN ws < 2  THEN 'Light (1-2 m/s)'
        WHEN ws < 4  THEN 'Moderate (2-4 m/s)'
        ELSE              'Strong (>4 m/s)'
    END                 AS wind_category,
    ROUND(AVG(pm25), 2) AS avg_pm25,
    COUNT(*)            AS readings
FROM measurements
WHERE ws IS NOT NULL AND pm25 IS NOT NULL
GROUP BY wind_category
ORDER BY avg_pm25 DESC;

-- Q8: Weekend vs weekday pollution comparison
SELECT
    CASE CAST(strftime('%w', ts) AS INTEGER)
        WHEN 0 THEN 'Weekend'
        WHEN 6 THEN 'Weekend'
        ELSE        'Weekday'
    END                 AS day_type,
    ROUND(AVG(pm25), 2) AS avg_pm25,
    ROUND(AVG(no2), 2)  AS avg_no2,
    ROUND(AVG(co), 2)   AS avg_co,
    COUNT(*)            AS readings
FROM measurements
WHERE pm25 IS NOT NULL
GROUP BY day_type;

-- Q9: Rolling 7-day average PM2.5 (for trend visualization)
SELECT
    DATE(ts)           AS day,
    ROUND(AVG(pm25), 2) AS daily_avg,
    ROUND(AVG(AVG(pm25)) OVER (
        ORDER BY DATE(ts) ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ), 2)              AS rolling_7day_avg
FROM measurements
WHERE pm25 IS NOT NULL
GROUP BY DATE(ts)
ORDER BY day;

-- Q10: AQI category distribution (how many days in each bucket)
SELECT
    aqi_category,
    COUNT(*)           AS days,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM daily_summary
WHERE aqi_category IS NOT NULL
GROUP BY aqi_category
ORDER BY days DESC;