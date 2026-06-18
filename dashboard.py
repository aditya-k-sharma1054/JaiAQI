"""
dashboard.py — Jaipur Air Quality Analytics Portal
Run: python -m streamlit run dashboard.py
"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import text

from src.load.load import get_engine
from src.common.config import NAAQS, AQI_BINS, AQI_LABELS, DATA_DIR

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Jaipur Air Quality Analytics",
    page_icon="🌬️",
    layout="wide",
    initial_sidebar_state="expanded",
)

AQI_COLORS = {
    "Good":         "#00b050",
    "Satisfactory": "#92d050",
    "Moderate":     "#ffff00",
    "Poor":         "#ff9900",
    "Very Poor":    "#ff0000",
    "Severe":       "#c00000",
}

POLL_LABELS = {
    "pm25":  "PM2.5 (µg/m³)",
    "pm10":  "PM10 (µg/m³)",
    "no2":   "NO₂ (µg/m³)",
    "so2":   "SO₂ (µg/m³)",
    "co":    "CO (mg/m³)",
    "ozone": "Ozone (µg/m³)",
    "no":    "NO (µg/m³)",
    "nh3":   "NH₃ (µg/m³)",
}

# ── Data layer ────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def _engine():
    return get_engine()

@st.cache_data(show_spinner=False, ttl=3600)
def load_stations() -> pd.DataFrame:
    return pd.read_sql("SELECT station_id, station_name FROM stations", _engine())

@st.cache_data(show_spinner=False, ttl=3600)
def load_measurements() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM measurements ORDER BY ts", _engine(), parse_dates=["ts"])

@st.cache_data(show_spinner=False, ttl=3600)
def load_daily() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM daily_summary ORDER BY summary_date", _engine(), parse_dates=["summary_date"])

@st.cache_data(show_spinner=False)
def load_insights() -> dict:
    p = DATA_DIR / "processed" / "insights.json"
    return json.loads(p.read_text()) if p.exists() else {}

# ── Helpers ───────────────────────────────────────────────────────────────────
LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font_color="#e0e0e0",
    yaxis=dict(gridcolor="#2a2a2a"),
    xaxis=dict(gridcolor="#2a2a2a"),
    margin=dict(t=30, b=20),
)

def aqi_cat(v):
    for lo, hi, label in zip(AQI_BINS, AQI_BINS[1:], AQI_LABELS):
        if lo <= v < hi:
            return label
    return "Severe"

# ── Sidebar ───────────────────────────────────────────────────────────────────

def sidebar_header():
    st.sidebar.title("🌬️ Jaipur AQI")
    st.sidebar.markdown("**City:** Jaipur, Rajasthan")
    st.sidebar.markdown("**Source:** CPCB-CCR / RSPCB")
    st.sidebar.divider()


def sidebar_filters(df_raw: pd.DataFrame, sid_map: dict):

    st.sidebar.subheader("Station")
    name_options = ["All Stations"] + sorted(sid_map.values())
    station_sel = st.sidebar.selectbox("Station", name_options)

    df = df_raw.copy()

    if station_sel != "All Stations":
        sel_id = [k for k, v in sid_map.items() if v == station_sel][0]
        df = df[df["station_id"] == sel_id]

    st.sidebar.subheader("Date Range")

    min_d = df_raw["ts"].dt.date.min()
    max_d = df_raw["ts"].dt.date.max()

    d_from = st.sidebar.date_input(
        "From",
        value=min_d,
        min_value=min_d,
        max_value=max_d
    )

    d_to = st.sidebar.date_input(
        "To",
        value=max_d,
        min_value=min_d,
        max_value=max_d
    )

    st.sidebar.subheader("Primary Pollutant")

    pollutant = st.sidebar.selectbox(
        "Pollutant",
        list(POLL_LABELS.keys()),
        format_func=lambda x: POLL_LABELS[x]
    )

    st.sidebar.subheader("Aggregation")

    agg = st.sidebar.radio(
        "View as",
        ["15-min raw", "Hourly avg", "Daily avg"]
    )

    st.sidebar.divider()

    st.sidebar.caption(
        f"Dataset: {len(df_raw):,} rows · 6 stations\n"
        f"{min_d} → {max_d}"
    )

    return df, d_from, d_to, pollutant, agg, station_sel

# ── Page 1: Overview ──────────────────────────────────────────────────────────
def page_overview(df_raw, df_daily, insights):
    st.title("Jaipur Air Quality Analytics Portal")
    st.caption("6 CPCB Stations · Full Year 2025 · 15-min granularity · RSPCB")
    st.divider()

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Annual Avg PM2.5",    f"{df_raw['pm25'].mean():.1f} µg/m³",
              f"NAAQS: {NAAQS['pm25']} µg/m³")
    c2.metric("Peak PM2.5",          f"{df_raw['pm25'].max():.1f} µg/m³", delta_color="inverse")
    c3.metric("NAAQS Exceedance Days",
              str(insights.get("naaqs_exceed_days", "—")),
              f"{insights.get('naaqs_exceed_pct', '')}% of year", delta_color="inverse")
    c4.metric("Worst Month",  insights.get("worst_month", "—"),
              f"Avg {insights.get('worst_month_pm25', '')} µg/m³", delta_color="inverse")
    c5.metric("Best Month",   insights.get("best_month", "—"),
              f"Avg {insights.get('best_month_pm25', '')} µg/m³")

    st.divider()
    col_l, col_r = st.columns([1, 2])

    with col_l:
        st.subheader("AQI Category Distribution")
        cat_counts = df_daily["aqi_category"].value_counts().reset_index()
        cat_counts.columns = ["category", "days"]
        fig = px.pie(cat_counts, values="days", names="category",
                     color="category", color_discrete_map=AQI_COLORS, hole=0.55)
        fig.update_layout(**{**LAYOUT, "legend": dict(orientation="h", y=-0.1)})
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        st.subheader("Monthly PM2.5 Trend")
        df_raw["month"] = df_raw["ts"].dt.to_period("M").astype(str)
        monthly = df_raw.groupby("month")["pm25"].mean().reset_index()
        monthly.columns = ["month", "avg_pm25"]
        monthly["cat"] = monthly["avg_pm25"].apply(aqi_cat)
        fig2 = px.bar(monthly, x="month", y="avg_pm25",
                      color="cat", color_discrete_map=AQI_COLORS,
                      labels={"avg_pm25": "Avg PM2.5 (µg/m³)", "month": ""},
                      text="avg_pm25")
        fig2.add_hline(y=NAAQS["pm25"], line_dash="dash", line_color="#ff9900",
                       annotation_text="NAAQS 60 µg/m³")
        fig2.update_traces(texttemplate="%{text:.0f}", textposition="outside")
        fig2.update_layout(**{**LAYOUT, "showlegend": False})
        st.plotly_chart(fig2, use_container_width=True)

# ── Page 2: Station Comparison ────────────────────────────────────────────────
def page_station_comparison(df_raw, df_daily, sid_map):
    st.title("Station Comparison")
    st.caption("How do Jaipur's 6 monitoring stations compare?")
    st.divider()

    df_raw   = df_raw.copy()
    df_daily = df_daily.copy()
    df_raw["station_name"]   = df_raw["station_id"].map(sid_map)
    df_daily["station_name"] = df_daily["station_id"].map(sid_map)

    # Ranked bar
    st.subheader("Annual Average PM2.5 — Station Ranking")
    rank = df_raw.groupby("station_name")["pm25"].mean().reset_index()
    rank.columns = ["Station", "Avg PM2.5"]
    rank = rank.sort_values("Avg PM2.5", ascending=False)
    rank["cat"] = rank["Avg PM2.5"].apply(aqi_cat)
    fig = px.bar(rank, x="Station", y="Avg PM2.5",
                 color="cat", color_discrete_map=AQI_COLORS, text="Avg PM2.5")
    fig.add_hline(y=NAAQS["pm25"], line_dash="dash", line_color="#ff9900",
                  annotation_text="NAAQS 60")
    fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
    fig.update_layout(**{**LAYOUT, "showlegend": False})
    st.plotly_chart(fig, use_container_width=True)

    # Monthly trend all stations
    st.subheader("Monthly PM2.5 Trend — All Stations")
    df_raw["month_str"] = df_raw["ts"].dt.to_period("M").astype(str)
    ms = df_raw.groupby(["month_str","station_name"])["pm25"].mean().reset_index()
    ms.columns = ["Month", "Station", "Avg PM2.5"]
    fig2 = px.line(ms, x="Month", y="Avg PM2.5", color="Station", markers=True)
    fig2.add_hline(y=NAAQS["pm25"], line_dash="dash", line_color="#ff9900",
                   annotation_text="NAAQS")
    fig2.update_layout(**LAYOUT)
    st.plotly_chart(fig2, use_container_width=True)

    # Heatmap: station × month
    st.subheader("PM2.5 Heatmap — Station × Month")
    df_daily["month_str"] = pd.to_datetime(df_daily["summary_date"]).dt.to_period("M").astype(str)
    heat = df_daily.groupby(["station_name","month_str"])["avg_pm25"].mean().reset_index()
    pivot = heat.pivot(index="station_name", columns="month_str", values="avg_pm25").round(1)
    fig3 = px.imshow(pivot, color_continuous_scale="RdYlGn_r",
                     zmin=20, zmax=120, labels=dict(color="Avg PM2.5"), text_auto=".0f")
    fig3.update_layout(**{**LAYOUT, "margin": dict(t=20)})
    st.plotly_chart(fig3, use_container_width=True)

    # Worst day per station
    st.subheader("Worst Recorded Day per Station")
    worst = df_daily.loc[df_daily.groupby("station_name")["avg_pm25"].idxmax()][
        ["station_name","summary_date","avg_pm25","aqi_category"]].copy()
    worst.columns = ["Station","Date","Avg PM2.5","AQI Category"]
    st.dataframe(worst.sort_values("Avg PM2.5", ascending=False),
                 use_container_width=True, hide_index=True)

# ── Page 3: Story ─────────────────────────────────────────────────────────────
def page_story(df_raw, insights):
    st.title("What the Data Tells Us")
    st.caption("Patterns and insights — not just numbers.")
    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 🕐 Best & Worst Hours to Step Outside")
        hourly = df_raw.groupby(df_raw["ts"].dt.hour)["pm25"].mean().reset_index()
        hourly.columns = ["hour", "avg_pm25"]
        hourly["label"] = hourly["hour"].apply(lambda h: f"{h:02d}:00")
        fig = px.line(hourly, x="label", y="avg_pm25", markers=True,
                      labels={"avg_pm25": "Avg PM2.5 (µg/m³)", "label": "Hour"})
        fig.add_hline(y=NAAQS["pm25"], line_dash="dash", line_color="#ff9900",
                      annotation_text="NAAQS")
        fig.update_layout(**LAYOUT)
        st.plotly_chart(fig, use_container_width=True)
        st.info(f"✅ **Best time:** {insights.get('best_hour','—')} · {insights.get('best_hour_pm25','')} µg/m³")
        st.warning(f"⚠️ **Worst time:** {insights.get('worst_hour','—')} · {insights.get('worst_hour_pm25','')} µg/m³")
        st.markdown("_Temperature inversions trap pollution at night. Traffic causes a secondary 7–10 AM spike._")

    with col2:
        st.markdown("### 💨 Does Wind Clean the Air?")
        dw = df_raw[df_raw["ws"].notna() & df_raw["pm25"].notna()].copy()
        dw["wind_bin"] = pd.cut(dw["ws"], bins=[0,1,2,3,5,100],
                                labels=["<1 m/s","1–2","2–3","3–5",">5"])
        wa = dw.groupby("wind_bin", observed=True)["pm25"].mean().reset_index()
        fig2 = px.bar(wa, x="wind_bin", y="pm25",
                      labels={"wind_bin": "Wind Speed", "pm25": "Avg PM2.5"},
                      color="pm25", color_continuous_scale="RdYlGn_r")
        fig2.update_layout(**{**LAYOUT, "coloraxis_showscale": False})
        st.plotly_chart(fig2, use_container_width=True)
        st.info(
            f"🌬️ Calm (<1 m/s): **{insights.get('calm_pm25','—')} µg/m³** | "
            f"Windy (>3 m/s): **{insights.get('windy_pm25','—')} µg/m³**\n\n"
            f"Wind cuts PM2.5 by ~**{insights.get('wind_lift','—')} µg/m³**."
        )

    st.divider()
    col3, col4 = st.columns(2)

    with col3:
        st.markdown("### 📅 Weekday vs Weekend")
        df_raw["dow_type"] = df_raw["ts"].dt.dayofweek.apply(
            lambda d: "Weekend" if d >= 5 else "Weekday")
        wk = df_raw.groupby("dow_type")["pm25"].mean().reset_index()
        fig3 = px.bar(wk, x="dow_type", y="pm25",
                      color="dow_type",
                      color_discrete_map={"Weekday":"#4e9af1","Weekend":"#f1c40f"},
                      labels={"pm25":"Avg PM2.5 (µg/m³)","dow_type":""},
                      text="pm25")
        fig3.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig3.update_layout(**{**LAYOUT, "showlegend": False})
        st.plotly_chart(fig3, use_container_width=True)
        wkd = insights.get("weekday_pm25", 0)
        wke = insights.get("weekend_pm25", 0)
        diff = round(abs(wkd - wke), 1)
        if wkd > wke:
            st.markdown(f"Weekdays are **{diff} µg/m³ worse** — traffic dominates.")
        else:
            st.markdown(f"Weekends are **{diff} µg/m³ worse** — possible waste burning or festivities.")

    with col4:
        st.markdown("### 📦 Pollutant Mix")
        polls = ["pm25","pm10","no2","so2","co","ozone"]
        polls = [p for p in polls if p in df_raw.columns]
        avgs  = {POLL_LABELS.get(p,p): round(df_raw[p].mean(), 2) for p in polls if df_raw[p].notna().any()}
        fig4 = px.bar(x=list(avgs.keys()), y=list(avgs.values()),
                      color=list(avgs.values()), color_continuous_scale="Reds",
                      labels={"x":"Pollutant","y":"Annual Average"})
        fig4.update_layout(**{**LAYOUT, "showlegend": False, "coloraxis_showscale": False})
        st.plotly_chart(fig4, use_container_width=True)

# ── Page 4: Advanced Search ───────────────────────────────────────────────────
def page_advanced_search(df_raw, d_from, d_to, pollutant, agg):
    st.title("Advanced Search & Report")
    st.caption("Filter by date, pollutant, and aggregation — then export.")
    st.divider()

    mask = (df_raw["ts"].dt.date >= d_from) & (df_raw["ts"].dt.date <= d_to)
    df_f = df_raw[mask].copy()
    if df_f.empty:
        st.warning("No data for selected range.")
        return

    if agg == "15-min raw":
        df_plot = df_f[["ts", pollutant]].dropna()
    elif agg == "Hourly avg":
        df_plot = df_f.set_index("ts")[pollutant].resample("1h").mean().reset_index()
        df_plot.columns = ["ts", pollutant]
    else:
        df_plot = df_f.set_index("ts")[pollutant].resample("1D").mean().reset_index()
        df_plot.columns = ["ts", pollutant]
    df_plot = df_plot.dropna()

    s = df_f[pollutant].dropna()
    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("Records",  f"{len(s):,}")
    c2.metric("Average",  f"{s.mean():.2f}")
    c3.metric("Maximum",  f"{s.max():.2f}")
    c4.metric("Minimum",  f"{s.min():.2f}")
    c5.metric("95th pct", f"{s.quantile(0.95):.2f}")

    std = NAAQS.get(pollutant)
    if std:
        exceed_pct = (s > std).mean() * 100
        if exceed_pct > 0:
            st.error(f"⚠️ {exceed_pct:.1f}% of readings exceed NAAQS standard ({std})")
        else:
            st.success(f"✅ All readings within NAAQS standard ({std})")

    fig = px.line(df_plot, x="ts", y=pollutant,
                  labels={"ts":"Timestamp", pollutant: POLL_LABELS.get(pollutant, pollutant)})
    if std:
        fig.add_hline(y=std, line_dash="dash", line_color="#ff9900",
                      annotation_text=f"NAAQS {std}")
    fig.update_layout(**LAYOUT)
    st.plotly_chart(fig, use_container_width=True)

    with st.expander("📋 View Data Table"):
        st.dataframe(df_plot, use_container_width=True, height=300)

    csv = df_plot.to_csv(index=False).encode()
    st.download_button("⬇ Export CSV", csv,
                       file_name=f"jaipur_{pollutant}_{d_from}_{d_to}.csv",
                       mime="text/csv")

# ── Page 5: Data Quality ──────────────────────────────────────────────────────
def page_data_quality(df_raw):
    st.title("Data Quality Report")
    st.caption("Completeness and reliability of CPCB observations.")
    st.divider()

    polls = [p for p in ["pm25","pm10","no2","so2","co","ozone","no","nh3"] if p in df_raw.columns]

    df_raw["month"] = df_raw["ts"].dt.month
    rows = []
    for p in polls:
        for m, pct in df_raw.groupby("month")[p].apply(lambda x: x.notna().mean()*100).items():
            rows.append({"Pollutant": POLL_LABELS.get(p,p), "Month": m, "Availability %": round(pct,1)})

    dq = pd.DataFrame(rows)
    month_map = {1:"Jan",2:"Feb",3:"Mar",4:"Apr",5:"May",6:"Jun",
                 7:"Jul",8:"Aug",9:"Sep",10:"Oct",11:"Nov",12:"Dec"}
    dq["Month"] = dq["Month"].map(month_map)
    pivot = dq.pivot(index="Pollutant", columns="Month", values="Availability %")
    order = [m for m in ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"] if m in pivot.columns]
    pivot = pivot[order]

    fig = px.imshow(pivot, color_continuous_scale="RdYlGn", zmin=0, zmax=100,
                    labels=dict(color="Availability %"), text_auto=".0f")
    fig.update_layout(**{**LAYOUT, "margin": dict(t=20)})
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Overall Completeness")
    summary = []
    for p in polls:
        col = df_raw[p]
        summary.append({
            "Pollutant":      POLL_LABELS.get(p,p),
            "Total Readings": len(col),
            "Valid":          int(col.notna().sum()),
            "Missing":        int(col.isna().sum()),
            "Availability":   f"{col.notna().mean()*100:.1f}%",
            "Mean":           f"{col.mean():.2f}" if col.notna().any() else "—",
            "Max":            f"{col.max():.2f}"  if col.notna().any() else "—",
        })
    st.dataframe(pd.DataFrame(summary), use_container_width=True)

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    try:
        df_raw = load_measurements()
        df_daily = load_daily()
        insights = load_insights()
        sdf = load_stations()

        sid_map = dict(
            zip(
                sdf["station_id"],
                sdf["station_name"]
            )
        )

    except Exception as e:
        st.error(
            f"Database not ready. Run `python run_pipeline.py` first.\n\n`{e}`"
        )
        st.stop()

    sidebar_header()

    page = st.sidebar.radio(
        "Navigate",
        [
            "📊 Overview",
            "🏙️ Station Comparison",
            "💡 What the Data Tells Us",
            "🔍 Advanced Search",
            "🔬 Data Quality"
        ],
        label_visibility="collapsed",
    )

    if page == "🔍 Advanced Search":

        (
            df_filtered,
            d_from,
            d_to,
            pollutant,
            agg,
            station_sel,
        ) = sidebar_filters(df_raw, sid_map)

    else:

        df_filtered = df_raw
        d_from = None
        d_to = None
        pollutant = None
        agg = None

    if page == "📊 Overview":
        page_overview(df_filtered, df_daily, insights)

    elif page == "🏙️ Station Comparison":
        page_station_comparison(df_raw, df_daily, sid_map)

    elif page == "💡 What the Data Tells Us":
        page_story(df_filtered, insights)

    elif page == "🔍 Advanced Search":
        page_advanced_search(
            df_filtered,
            d_from,
            d_to,
            pollutant,
            agg,
        )

    elif page == "🔬 Data Quality":
        page_data_quality(df_filtered)


if __name__ == "__main__":
    main()