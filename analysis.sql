-- analysis.sql
-- Tajir Demand Forecaster — SQL Analysis Queries
-- Run against the SQLite database built from sales/stores/products CSVs
-- These queries surface actionable supply-chain insights for Tajir

-- ─────────────────────────────────────────────────────────────
-- Q1: Which products are most at risk of stockout? (last 7 days)
--     High velocity + low restock threshold = danger zone
-- ─────────────────────────────────────────────────────────────
SELECT
    p.name                                        AS product,
    p.category,
    p.restock_threshold,
    ROUND(AVG(s.units_sold), 1)                   AS avg_daily_units,
    ROUND(p.restock_threshold / AVG(s.units_sold), 1) AS days_to_empty
FROM sales s
JOIN products p ON s.product_id = p.product_id
WHERE s.date >= DATE('now', '-7 days')
GROUP BY s.product_id
HAVING avg_daily_units > 0
ORDER BY days_to_empty ASC
LIMIT 10;


-- ─────────────────────────────────────────────────────────────
-- Q2: Store revenue ranking — which stores drive most GMV?
-- ─────────────────────────────────────────────────────────────
SELECT
    st.name                         AS store,
    st.area,
    SUM(s.revenue)                  AS total_revenue,
    SUM(s.units_sold)               AS total_units,
    ROUND(AVG(s.revenue), 0)        AS avg_daily_revenue,
    COUNT(DISTINCT s.date)          AS active_days
FROM sales s
JOIN stores st ON s.store_id = st.store_id
GROUP BY s.store_id
ORDER BY total_revenue DESC;


-- ─────────────────────────────────────────────────────────────
-- Q3: Weekend vs Weekday demand split
--     (Fri=4, Sat=5 in SQLite strftime %w where 0=Sunday)
-- ─────────────────────────────────────────────────────────────
SELECT
    p.name                                           AS product,
    ROUND(AVG(CASE WHEN CAST(strftime('%w', s.date) AS INT) IN (5,6)
                   THEN s.units_sold END), 1)        AS weekend_avg,
    ROUND(AVG(CASE WHEN CAST(strftime('%w', s.date) AS INT) NOT IN (5,6)
                   THEN s.units_sold END), 1)        AS weekday_avg,
    ROUND(
        AVG(CASE WHEN CAST(strftime('%w', s.date) AS INT) IN (5,6)
                 THEN s.units_sold END) /
        AVG(CASE WHEN CAST(strftime('%w', s.date) AS INT) NOT IN (5,6)
                 THEN s.units_sold END),
    2)                                               AS weekend_multiplier
FROM sales s
JOIN products p ON s.product_id = p.product_id
GROUP BY s.product_id
ORDER BY weekend_multiplier DESC;


-- ─────────────────────────────────────────────────────────────
-- Q4: Monthly sales trend — are stores growing?
-- ─────────────────────────────────────────────────────────────
SELECT
    strftime('%Y-%m', s.date)   AS month,
    st.name                     AS store,
    SUM(s.revenue)              AS monthly_revenue,
    SUM(s.units_sold)           AS monthly_units
FROM sales s
JOIN stores st ON s.store_id = st.store_id
GROUP BY month, s.store_id
ORDER BY month ASC, monthly_revenue DESC;


-- ─────────────────────────────────────────────────────────────
-- Q5: Top 5 revenue-generating products per store
-- ─────────────────────────────────────────────────────────────
SELECT
    st.name         AS store,
    p.name          AS product,
    p.category,
    SUM(s.revenue)  AS total_revenue,
    SUM(s.units_sold) AS total_units
FROM sales s
JOIN stores  st ON s.store_id   = st.store_id
JOIN products p ON s.product_id = p.product_id
GROUP BY s.store_id, s.product_id
QUALIFY ROW_NUMBER() OVER (PARTITION BY s.store_id ORDER BY SUM(s.revenue) DESC) <= 5
ORDER BY st.name, total_revenue DESC;


-- ─────────────────────────────────────────────────────────────
-- Q6: Delivery consolidation opportunity
--     How many separate "orders" could be merged per day?
--     Each store×day with sales = 1 potential Tajir delivery
--     vs traditional model (1 delivery per product supplier = up to 10/day)
-- ─────────────────────────────────────────────────────────────
SELECT
    s.date,
    COUNT(DISTINCT s.store_id)                          AS stores_ordering,
    COUNT(DISTINCT s.store_id) * 10                     AS traditional_truck_trips,
    COUNT(DISTINCT s.store_id)                          AS tajir_truck_trips,
    (COUNT(DISTINCT s.store_id) * 10)
        - COUNT(DISTINCT s.store_id)                    AS trips_saved,
    ROUND(((COUNT(DISTINCT s.store_id) * 10)
        - COUNT(DISTINCT s.store_id)) * 1.0
        / (COUNT(DISTINCT s.store_id) * 10) * 100, 1)  AS pct_reduction
FROM sales s
GROUP BY s.date
ORDER BY s.date DESC
LIMIT 30;
