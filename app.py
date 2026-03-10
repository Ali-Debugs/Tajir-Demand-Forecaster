"""
app.py — Tajir Demand Forecaster
=================================
A dashboard for Pakistani kiryana store owners to:
  1. See their sales overview
  2. Forecast next N days of demand per product
  3. Get restock alerts before stock runs out
  4. Explore data using live SQL queries
  5. Simulate Tajir's delivery consolidation impact

Run:  streamlit run app.py
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import sqlite3

from forecaster import train_and_forecast, get_restock_alerts

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Tajir Demand Forecaster",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Minimal CSS ───────────────────────────────────────────────────────────────
# We only style the KPI card. Everything else uses Streamlit native components
# so dark mode works automatically — no hardcoded light/dark colors anywhere.
st.markdown("""
<style>
.kpi-card {
    padding: 16px 20px;
    border-radius: 8px;
    border: 1px solid rgba(0, 176, 80, 0.4);
    border-left: 4px solid #00b050;
}
.kpi-label { font-size: 11px; opacity: 0.55; text-transform: uppercase; letter-spacing: 0.6px; }
.kpi-value { font-size: 26px; font-weight: 700; color: #00b050; margin: 4px 0; }
.kpi-sub   { font-size: 11px; opacity: 0.45; }
</style>
""", unsafe_allow_html=True)


# ── Data loading ──────────────────────────────────────────────────────────────
import os
if not os.path.exists("data/sales.csv"):
    import generate_data
    generate_data.main()


@st.cache_data
def load_data():
    """Read the three CSVs produced by generate_data.py — cached after first load."""
    sales    = pd.read_csv("data/sales.csv",    parse_dates=["date"])
    stores   = pd.read_csv("data/stores.csv")
    products = pd.read_csv("data/products.csv")
    return sales, stores, products

@st.cache_resource
def get_db():
    """
    Load the CSVs into an in-memory SQLite database once.
    @st.cache_resource keeps the connection alive across reruns.
    """
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    sales, stores, products = load_data()
    sales.to_sql("sales",     conn, index=False, if_exists="replace")
    stores.to_sql("stores",   conn, index=False, if_exists="replace")
    products.to_sql("products", conn, index=False, if_exists="replace")
    return conn

sales_df, stores_df, products_df = load_data()
db_conn = get_db()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.title("🛒 Tajir")
    st.caption("Demand Forecaster")
    st.divider()

    # Build name→id lookup from the stores table
    store_map           = dict(zip(stores_df["name"], stores_df["store_id"]))
    selected_store_name = st.selectbox("Select Store", list(store_map.keys()))
    selected_store_id   = store_map[selected_store_name]

    store_row = stores_df[stores_df["store_id"] == selected_store_id].iloc[0]
    st.caption(f"📍 {store_row['area']}  ·  Owner: {store_row['owner']}")

    st.divider()
    st.markdown("**Forecast Settings**")
    forecast_horizon = st.slider("Days ahead", min_value=3, max_value=14, value=7)

    all_categories = products_df["category"].unique().tolist()
    selected_cats  = st.multiselect("Categories", all_categories, default=all_categories)

    st.divider()
    st.caption("Stack: Python · Scikit-learn · SQLite · Streamlit · Plotly")


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 🛒 Tajir Demand Forecaster")
st.caption(f"**{selected_store_name}** · {store_row['area']}, Lahore")
st.divider()


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📊 Overview",
    "📈 Forecasts",
    "⚠️ Restock Alerts",
    "🗣️ Customer Voice",
    "🛢️ SQL Analysis",
    "🚚 Delivery Simulator",
])


# ═════════════════════════════════════════════════════════════════════════════
# TAB 1 — OVERVIEW
# KPIs, revenue trend, category breakdown, top products for the selected store.
# ═════════════════════════════════════════════════════════════════════════════
with tab1:
    store_sales = sales_df[sales_df["store_id"] == selected_store_id]

    # Summary numbers
    total_revenue = store_sales["revenue"].sum()
    total_units   = store_sales["units_sold"].sum()
    avg_daily_rev = store_sales.groupby("date")["revenue"].sum().mean()
    top_pid       = store_sales.groupby("product_id")["units_sold"].sum().idxmax()
    top_product   = products_df[products_df["product_id"] == top_pid]["name"].values[0]

    # KPI cards — only 4 lines of CSS used, all transparent background
    c1, c2, c3, c4 = st.columns(4)
    for col, label, value, sub in [
        (c1, "Total Revenue",  f"Rs {total_revenue/1000:.0f}K", "6 months"),
        (c2, "Units Sold",     f"{total_units:,}",               "6 months"),
        (c3, "Avg Daily Rev",  f"Rs {avg_daily_rev:.0f}",         "per day"),
        (c4, "Top Product",    top_product[:20],                  "by volume"),
    ]:
        col.markdown(
            f'<div class="kpi-card">'
            f'<div class="kpi-label">{label}</div>'
            f'<div class="kpi-value">{value}</div>'
            f'<div class="kpi-sub">{sub}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.markdown("#### Daily Revenue Trend")
    st.caption("Bars = daily revenue · Line = 7-day rolling average")

    daily = store_sales.groupby("date")["revenue"].sum().reset_index()
    daily["rolling_7"] = daily["revenue"].rolling(7).mean()

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Bar(
        x=daily["date"], y=daily["revenue"],
        name="Daily Revenue",
        marker_color="rgba(0,176,80,0.3)",
        hovertemplate="Rs %{y:,.0f}<extra></extra>",
    ))
    fig_trend.add_trace(go.Scatter(
        x=daily["date"], y=daily["rolling_7"],
        name="7-day avg",
        line=dict(color="#00b050", width=2),
        hovertemplate="Rs %{y:,.0f}<extra></extra>",
    ))
    fig_trend.update_layout(
        height=300, margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="rgba(128,128,128,0.15)"),
        legend=dict(orientation="h", y=1.15),
        hovermode="x unified",
    )
    st.plotly_chart(fig_trend, width="stretch")

    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### Sales by Category")
        cat_sales = store_sales.merge(products_df[["product_id", "category"]], on="product_id")
        cat_agg   = cat_sales.groupby("category")["revenue"].sum().reset_index()
        fig_pie = px.pie(
            cat_agg, values="revenue", names="category",
            color_discrete_sequence=px.colors.sequential.Greens_r,
        )
        fig_pie.update_layout(
            height=280, margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="h"),
        )
        fig_pie.update_traces(textposition="inside", textinfo="percent+label")
        st.plotly_chart(fig_pie, width="stretch")

    with col_b:
        st.markdown("#### Top 5 Products by Volume")
        top5 = (
            store_sales.merge(products_df[["product_id", "name"]], on="product_id")
            .groupby("name")["units_sold"].sum()
            .nlargest(5).reset_index()
        )
        fig_bar = px.bar(
            top5, x="units_sold", y="name", orientation="h",
            color_discrete_sequence=["#00b050"],
        )
        fig_bar.update_layout(
            height=280, margin=dict(l=0, r=0, t=0, b=0),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(title="Units Sold", showgrid=False),
            yaxis=dict(title="", autorange="reversed"),
        )
        st.plotly_chart(fig_bar, width="stretch")


# ═════════════════════════════════════════════════════════════════════════════
# TAB 2 — FORECASTS
# Trains a Ridge Regression model from forecaster.py and plots the prediction.
# ═════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("#### Product Demand Forecast")
    st.caption("Model: Ridge Regression with lag + seasonal features · trained on 6 months of daily sales")

    filtered_prods = products_df[products_df["category"].isin(selected_cats)]
    chosen_product = st.selectbox("Select product", filtered_prods["name"].tolist())
    product_id     = int(filtered_prods[filtered_prods["name"] == chosen_product]["product_id"].values[0])

    with st.spinner("Training model and generating forecast..."):
        forecast_df = train_and_forecast(selected_store_id, product_id, sales_df, forecast_horizon)

    if forecast_df is None:
        st.warning("Not enough historical data to forecast this product.")
    else:
        history = sales_df[
            (sales_df["store_id"] == selected_store_id) &
            (sales_df["product_id"] == product_id)
        ].tail(30)

        fig_fc = go.Figure()
        fig_fc.add_trace(go.Scatter(
            x=history["date"], y=history["units_sold"],
            name="Historical sales",
            line=dict(color="rgba(128,128,128,0.8)", width=2),
            mode="lines+markers", marker=dict(size=4),
        ))
        fig_fc.add_trace(go.Scatter(
            x=forecast_df["date"], y=forecast_df["predicted_units"],
            name=f"{forecast_horizon}-day forecast",
            line=dict(color="#00b050", width=2.5, dash="dot"),
            mode="lines+markers",
            marker=dict(size=7, symbol="diamond"),
            fill="tozeroy", fillcolor="rgba(0,176,80,0.08)",
        ))
        # "Today" marker — timestamp in ms for Plotly's time axis
        today_ts = pd.Timestamp(history["date"].max()).timestamp() * 1000
        fig_fc.add_vline(
            x=today_ts, line_dash="dash",
            line_color="rgba(128,128,128,0.5)",
            annotation_text="Today",
        )
        fig_fc.update_layout(
            height=360, margin=dict(l=0, r=0, t=0, b=0),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(showgrid=False),
            yaxis=dict(title="Units / day", gridcolor="rgba(128,128,128,0.15)"),
            legend=dict(orientation="h", y=1.12),
            hovermode="x unified",
        )
        st.plotly_chart(fig_fc, width="stretch")

        m1, m2, m3 = st.columns(3)
        m1.metric("7-Day Total",    f"{forecast_df['predicted_units'].sum():.0f} units")
        m2.metric("Daily Average",  f"{forecast_df['predicted_units'].mean():.1f} units")
        peak_day = str(forecast_df.loc[forecast_df["predicted_units"].idxmax(), "date"])
        m3.metric("Peak Day",       peak_day)

        st.markdown("**Forecast table**")
        out = forecast_df.rename(columns={"date": "Date", "predicted_units": "Predicted Units"})
        st.dataframe(out.set_index("Date"), width="stretch")


# ═════════════════════════════════════════════════════════════════════════════
# TAB 3 — RESTOCK ALERTS
# Runs forecasts for every product and flags which will run out soon.
# ═════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown("#### Restock Intelligence")
    st.caption("Products ranked by days of stock remaining, based on forecast demand")

    with st.spinner("Forecasting all products..."):
        alerts = get_restock_alerts(
            selected_store_id, sales_df,
            products_df[products_df["category"].isin(selected_cats)],
        )

    critical = [a for a in alerts if "Critical" in a["restock_urgency"]]
    soon     = [a for a in alerts if "Soon"     in a["restock_urgency"]]
    ok_list  = [a for a in alerts if "OK"       in a["restock_urgency"]]

    col_c, col_s, col_o = st.columns(3)
    col_c.metric("🔴 Critical",     len(critical), help="Order today")
    col_s.metric("🟠 Order Soon",   len(soon),     help="Order within 2–4 days")
    col_o.metric("🟢 Well Stocked", len(ok_list))
    st.divider()

    rows = [{
        "Status":        a["restock_urgency"],
        "Product":       a["product_name"],
        "Category":      a["category"],
        "7-Day Demand":  int(a["forecast_7d"]),
        "Daily Avg":     a["daily_avg"],
        "Days to Empty": a["days_to_empty"],
    } for a in alerts]

    st.dataframe(
        pd.DataFrame(rows),
        width="stretch",
        hide_index=True,
        column_config={
            "Status":        st.column_config.TextColumn(width="small"),
            "Days to Empty": st.column_config.NumberColumn(format="%.1f d", width="small"),
            "7-Day Demand":  st.column_config.NumberColumn(width="small"),
        },
    )

    st.info(
        "💡 **Tajir insight:** Ordering 1 day ahead via the app consolidates all deliveries "
        "into a single next-day truck — replacing 10–20 daily salesperson visits per store."
    )


# ═════════════════════════════════════════════════════════════════════════════
# TAB 4 — CUSTOMER VOICE
# Simulated field interviews with kiryana store owners in Lahore.
# ═════════════════════════════════════════════════════════════════════════════
with tab4:
    st.markdown("#### What Store Owners Are Saying")
    st.caption("Simulated interviews with kiryana store owners in Lahore, January 2025")

    interviews = [
        {
            "urdu":    "Pehle 15 se 20 log aate thay order lene — ek din mein. Ab ek jagah se order kar do, kal aa jata hai.",
            "english": "Before, 15–20 people came to collect orders in a single day. Now order from one place, it arrives tomorrow.",
            "author":  "Muhammad Saleem · Gulberg Kiryana Store",
            "tag":     "✅ Positive",
        },
        {
            "urdu":    "Mujhe nahi pata hota tha kaunsa maal khatam hone wala hai. Ab app batati hai advance mein.",
            "english": "I never knew which stock was about to run out. Now the app tells me in advance.",
            "author":  "Hina Bibi · Model Town General Store",
            "tag":     "✅ Positive",
        },
        {
            "urdu":    "Delivery kabhi kabhi late hoti hai — kal ki jagah parson aa jaata hai. Yeh theek hona chahiye.",
            "english": "Delivery is sometimes late — arrives the day after tomorrow instead of tomorrow. This needs fixing.",
            "author":  "Tariq Mehmood · Johar Town Shop",
            "tag":     "⚠️ Mixed",
        },
        {
            "urdu":    "Paise online dena mushkil lagta hai. Cash option rehna chahiye.",
            "english": "Paying online feels difficult. The cash option should remain.",
            "author":  "Asif Iqbal · DHA Phase 4 Kiryana",
            "tag":     "⚠️ Concern",
        },
        {
            "urdu":    "Bahut faida hua hai. Pehle ek hafta wait karo, ab agli subah. Mera business behtar ho gaya hai.",
            "english": "Very beneficial. Before, wait a week. Now, next morning. My business has improved.",
            "author":  "Razia Sultana · Bahria Town Store",
            "tag":     "✅ Positive",
        },
    ]

    for iv in interviews:
        with st.container(border=True):
            st.markdown(f"*\"{iv['urdu']}\"*")
            st.caption(f"🌐 {iv['english']}")
            a, b = st.columns([4, 1])
            a.markdown(f"**{iv['author']}**")
            b.markdown(iv["tag"])

    st.divider()
    st.markdown("**Key insights from the field**")
    st.markdown("""
- Biggest pain: **10–20 salesperson visits per store per day** — Tajir eliminates this
- Owners want **advance stock visibility** — the core purpose of this tool
- **Delivery reliability** is the top complaint — predictive ordering helps
- **Cash on delivery** is still strongly preferred — important UX signal
""")


# ═════════════════════════════════════════════════════════════════════════════
# TAB 5 — SQL ANALYSIS
# Live SQL queries against a SQLite DB. Queries are editable — shows SQL skill.
# ═════════════════════════════════════════════════════════════════════════════
with tab5:
    st.markdown("#### Live SQL Analysis")
    st.caption("Queries run against a SQLite database with tables: `sales`, `stores`, `products`")

    QUERIES = {
        "🔴 Stockout Risk — days of stock remaining": """
SELECT
    p.name                                              AS product,
    p.category,
    p.restock_threshold                                 AS restock_at,
    ROUND(AVG(s.units_sold), 1)                         AS avg_daily_units,
    ROUND(p.restock_threshold / AVG(s.units_sold), 1)   AS days_to_empty
FROM sales s
JOIN products p ON s.product_id = p.product_id
GROUP BY s.product_id
HAVING avg_daily_units > 0
ORDER BY days_to_empty ASC
LIMIT 10""",

        "📦 Store Revenue Ranking": """
SELECT
    st.name                             AS store,
    st.area,
    SUM(s.revenue)                      AS total_revenue,
    SUM(s.units_sold)                   AS total_units,
    ROUND(AVG(s.revenue), 0)            AS avg_daily_revenue
FROM sales s
JOIN stores st ON s.store_id = st.store_id
GROUP BY s.store_id
ORDER BY total_revenue DESC""",

        "📅 Monthly Revenue Trend": """
SELECT
    strftime('%Y-%m', s.date)   AS month,
    st.name                     AS store,
    SUM(s.revenue)              AS monthly_revenue,
    SUM(s.units_sold)           AS monthly_units
FROM sales s
JOIN stores st ON s.store_id = st.store_id
GROUP BY month, s.store_id
ORDER BY month ASC""",

        "📆 Weekend vs Weekday Demand": """
SELECT
    p.name AS product,
    ROUND(AVG(CASE WHEN CAST(strftime('%w', s.date) AS INT) IN (5,6)
                   THEN CAST(s.units_sold AS FLOAT) END), 1) AS weekend_avg,
    ROUND(AVG(CASE WHEN CAST(strftime('%w', s.date) AS INT) NOT IN (5,6)
                   THEN CAST(s.units_sold AS FLOAT) END), 1) AS weekday_avg,
    ROUND(
        AVG(CASE WHEN CAST(strftime('%w', s.date) AS INT) IN (5,6)
                 THEN CAST(s.units_sold AS FLOAT) END) /
        AVG(CASE WHEN CAST(strftime('%w', s.date) AS INT) NOT IN (5,6)
                 THEN CAST(s.units_sold AS FLOAT) END)
    , 2) AS weekend_multiplier
FROM sales s
JOIN products p ON s.product_id = p.product_id
GROUP BY s.product_id
ORDER BY weekend_multiplier DESC""",

        "🚚 Daily Delivery Consolidation": """
SELECT
    s.date,
    COUNT(DISTINCT s.store_id)          AS stores_active,
    COUNT(DISTINCT s.store_id) * 10     AS traditional_trips,
    COUNT(DISTINCT s.store_id)          AS tajir_trips,
    COUNT(DISTINCT s.store_id) * 9      AS trips_saved
FROM sales s
GROUP BY s.date
ORDER BY s.date DESC
LIMIT 14""",
    }

    selected_q = st.selectbox("Choose a preset query", list(QUERIES.keys()))
    sql = st.text_area("SQL (editable — try modifying it!)", value=QUERIES[selected_q], height=155)

    run = st.button("▶ Run Query", type="primary")
    st.caption("Tables: `sales` · `stores` · `products`")

    # Run automatically when query changes, or when button is clicked
    query_changed = st.session_state.get("last_sql") != sql
    if run or query_changed:
        try:
            result = pd.read_sql_query(sql, db_conn)
            st.session_state["sql_result"] = result
            st.session_state["last_sql"]   = sql
        except Exception as e:
            st.error(f"SQL Error: {e}")
            result = None
    else:
        result = st.session_state.get("sql_result")

    if result is not None:
        st.caption(f"{len(result)} rows returned")
        st.dataframe(result, width="stretch", hide_index=True)

        # Auto-generate a bar chart when result has text + number columns
        num_cols = result.select_dtypes(include="number").columns.tolist()
        str_cols = result.select_dtypes(include="object").columns.tolist()
        if str_cols and num_cols and len(result) <= 30:
            fig_sql = px.bar(
                result.head(15),
                x=str_cols[0], y=num_cols[0],
                color_discrete_sequence=["#00b050"],
                title=f"{num_cols[0]} by {str_cols[0]}",
            )
            fig_sql.update_layout(
                height=280, margin=dict(l=0, r=0, t=40, b=0),
                plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor="rgba(128,128,128,0.15)"),
            )
            st.plotly_chart(fig_sql, width="stretch")

    with st.expander("📄 View full analysis.sql"):
        with open("analysis.sql") as f:
            st.code(f.read(), language="sql")


# ═════════════════════════════════════════════════════════════════════════════
# TAB 6 — DELIVERY SIMULATOR
# Interactive calculator for Tajir's core business value proposition.
# ═════════════════════════════════════════════════════════════════════════════
with tab6:
    st.markdown("#### Delivery Consolidation Simulator")
    st.caption("How many truck trips does Tajir eliminate? Adjust the sliders to find out.")

    st.info(
        "**The problem:** Each kiryana store is visited by 10–20 salespeople per day, "
        "each collecting a paper order and dispatching a separate truck. "
        "Tajir replaces all of that with one app order → one next-day delivery."
    )

    col_s1, col_s2, col_s3 = st.columns(3)
    num_stores          = col_s1.slider("Stores on Tajir",               1,   500,  50, step=5)
    suppliers_per_store = col_s2.slider("Supplier visits per store/day", 5,    25,  12)
    fuel_per_trip       = col_s3.slider("Fuel cost per trip (Rs)",       200, 2000, 800, step=100)

    # ── Calculations (each line is self-explanatory) ──────────────────────
    traditional_trips  = num_stores * suppliers_per_store   # every store × every supplier
    tajir_trips        = max(1, num_stores // 20)           # 1 Tajir truck serves ~20 stores
    trips_saved        = traditional_trips - tajir_trips
    pct_saved          = trips_saved / traditional_trips * 100
    fuel_saved_daily   = trips_saved * fuel_per_trip
    fuel_saved_monthly = fuel_saved_daily * 26              # ~26 working days per month
    co2_saved_kg       = trips_saved * 2.3                  # 2.3 kg CO₂ per urban truck trip

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Traditional Trips/Day", f"{traditional_trips:,}")
    k2.metric("Tajir Trips/Day",       f"{tajir_trips:,}",
              delta=f"-{trips_saved:,} saved", delta_color="inverse")
    k3.metric("Reduction",             f"{pct_saved:.0f}%")
    k4.metric("Fuel Saved / Month",    f"Rs {fuel_saved_monthly/1000:.0f}K")

    st.divider()

    # Side-by-side model comparison
    col_trad, col_tajir = st.columns(2)

    with col_trad:
        with st.container(border=True):
            st.markdown("#### ❌ Traditional Model")
            trucks = "🚛 " * min(traditional_trips, 24)
            extra  = f"  +{traditional_trips - 24} more" if traditional_trips > 24 else ""
            st.markdown(trucks + extra)
            st.markdown(f"""
- **{traditional_trips}** truck trips/day
- **{suppliers_per_store}** salespeople per store
- **Rs {traditional_trips * fuel_per_trip:,}** fuel/day
- **{traditional_trips * 2.3:.0f} kg** CO₂/day
""")

    with col_tajir:
        with st.container(border=True):
            st.markdown("#### ✅ Tajir Model")
            st.markdown("🚛 " * tajir_trips)
            st.markdown(f"""
- **{tajir_trips}** consolidated route(s)/day
- **1** app order per store — zero interruptions
- **Rs {tajir_trips * fuel_per_trip:,}** fuel/day
- **{tajir_trips * 2.3:.0f} kg** CO₂/day
""")

    st.divider()
    st.markdown("#### Efficiency scales with network size")
    st.caption("The gap between the lines is the value Tajir creates — it grows as more stores join")

    store_range = list(range(1, 501, 5))
    scale_df = pd.DataFrame({
        "Stores":      store_range,
        "Traditional": [s * suppliers_per_store for s in store_range],
        "Tajir":       [max(1, s // 20)          for s in store_range],
    })

    fig_scale = go.Figure()
    fig_scale.add_trace(go.Scatter(
        x=scale_df["Stores"], y=scale_df["Traditional"],
        name="Traditional", line=dict(color="#ef4444", width=2),
        fill="tozeroy", fillcolor="rgba(239,68,68,0.06)",
    ))
    fig_scale.add_trace(go.Scatter(
        x=scale_df["Stores"], y=scale_df["Tajir"],
        name="Tajir", line=dict(color="#00b050", width=2),
        fill="tozeroy", fillcolor="rgba(0,176,80,0.10)",
    ))
    fig_scale.add_vline(
        x=num_stores, line_dash="dash",
        line_color="rgba(128,128,128,0.5)",
        annotation_text=f"You → {num_stores} stores",
    )
    fig_scale.update_layout(
        height=300, margin=dict(l=0, r=0, t=0, b=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(title="Number of Stores", showgrid=False),
        yaxis=dict(title="Truck Trips / Day", gridcolor="rgba(128,128,128,0.15)"),
        legend=dict(orientation="h", y=1.12),
        hovermode="x unified",
    )
    st.plotly_chart(fig_scale, width="stretch")

    st.success(
        f"🌍 At **{num_stores} stores**, Tajir removes **{co2_saved_kg:.0f} kg of CO₂/day** — "
        f"like planting **{co2_saved_kg/120:.0f} trees**. "
        f"Scaled to Pakistan's **5M+ kiryana stores**, this is enormous."
    )


# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption(
    "Built by Ali-Debugs· "
    "Inspired by Tajir's mission to make Pakistan's economy radically more efficient · "
    "Stack: Python · Scikit-learn · SQLite · Streamlit · Plotly"
)
