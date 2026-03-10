# 🛒 Tajir Demand Forecaster

> An AI-powered demand forecasting dashboard for Pakistani kiryana stores — built to demonstrate how predictive analytics can radically reduce supply-chain inefficiency.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://tajir-demand-forecaster.streamlit.app)

---

## 💡 The Problem This Solves

Pakistani kiryana stores face a chaotic supply chain:

- Up to **20 salespeople** visit a single store per day to collect paper orders
- Store owners **don't know** what will run out until it's already gone
- Customers leave empty-handed → lost revenue for the store owner

This tool gives store owners **7-day ahead demand forecasts** so they can order once, in advance, via the Tajir app — consolidating deliveries and eliminating waste.

---

## 🚀 Quick Start

```bash
# 1. Clone the repo
git clone https://github.com/Ali-Debugs/tajir-demand-forecaster
cd tajir-demand-forecaster

# 2. Install dependencies
pip install -r requirements.txt

# 3. Generate synthetic data (run once)
python generate_data.py

# 4. Launch the dashboard
streamlit run app.py
```

---

## 🏗️ Project Structure

```
tajir-demand-forecaster/
│
├── app.py               # Streamlit dashboard — 6 tabs, ~630 lines
├── forecaster.py        # ML model — Ridge Regression with lag features
├── generate_data.py     # Synthetic data generator — 5 stores, 10 products, 6 months
├── analysis.sql         # SQL query library — 6 business queries
├── requirements.txt
├── data/
│   ├── sales.csv        # 9,050 daily sales records (generated)
│   ├── stores.csv       # 5 kiryana stores in Lahore
│   └── products.csv     # 10 common products with prices & restock thresholds

```

---

## 📊 Dashboard Tabs

| Tab | What it shows |
|-----|---------------|
| 📊 **Overview** | Revenue KPIs, daily trend chart, category breakdown, top 5 products |
| 📈 **Forecasts** | Historical + N-day ahead forecast chart for any product |
| ⚠️ **Restock Alerts** | All products ranked by urgency — Critical / Soon / OK |
| 🗣️ **Customer Voice** | Simulated field interviews with store owners (Urdu + English) |
| 🛢️ **SQL Analysis** | 5 live, editable SQL queries against a SQLite database |
| 🚚 **Delivery Simulator** | Interactive calculator showing how Tajir reduces truck trips |

---

## 🤖 ML Model

**File:** `forecaster.py`

**Algorithm:** Ridge Regression (regularized linear model — fast, interpretable, no overfitting)

**Features used to predict daily demand:**

| Feature | Why it matters |
|---------|----------------|
| `day_of_week` | Weekend sales spike in Pakistan (Fri/Sat) |
| `month` | Seasonal variation (winter, Ramadan) |
| `day_index` | Long-term growth trend |
| `lag_1` | Yesterday's sales is a strong predictor |
| `lag_7` | Same day last week |
| `rolling_7_mean` | Smoothed recent demand level |
| `rolling_7_std` | Demand volatility |

**Restock alert logic:**
```python
days_to_empty = restock_threshold / daily_avg_forecast
# 🔴 Critical  → days_to_empty < 2
# 🟠 Soon      → days_to_empty < 4
# 🟢 OK        → days_to_empty >= 4
```

---

## 🛢️ SQL Layer

**File:** `analysis.sql`

The app loads all three CSVs into an **in-memory SQLite database** on startup. The SQL Analysis tab runs live queries against it — queries are fully editable in the UI.

Preset queries answer real business questions:
1. Which products are closest to running out?
2. Which stores generate the most revenue?
3. How has revenue trended month over month?
4. Do weekend sales spike — and by how much?
5. How many truck trips does Tajir save per day?

---

## 🚚 Delivery Simulator

Tajir's core value: replace 10–20 daily supplier visits with **one consolidated next-day delivery**.

The simulator calculates:
- `traditional_trips = stores × suppliers_per_store`
- `tajir_trips = max(1, stores // 20)`  *(1 Tajir truck serves ~20 stores)*
- Fuel savings, CO₂ reduction, and a scaling curve showing how efficiency compounds

---

## 🗣️ Customer Interviews

Simulated field interviews with 5 kiryana store owners across Lahore (Gulberg, Model Town, Johar Town, DHA, Bahria Town). Quotes in Urdu with English translation.

**Key findings:**
- The biggest pain is **multiple daily salesperson visits** — Tajir directly eliminates this
- Store owners want **advance stock visibility** — the core purpose of this tool
- **Cash on delivery** is strongly preferred — important UX signal
- **Delivery reliability** is the top complaint

---

## 🔮 Potential Improvements

- Integrate real Tajir transaction data via API
- Upgrade to Facebook Prophet for better Ramadan/Eid seasonality
- Add WhatsApp alert link when a product hits Critical threshold
- Urdu UI toggle for store owner-facing view
- Multi-store comparison view

---

## 👤 About

Built as a portfolio project Inspired by Tajir App (2026).

Tajir's mission: *make a significant portion of Pakistan's economy radically more efficient.*

**Stack:** Python · Scikit-learn · SQLite · Streamlit · Plotly · Pandas
