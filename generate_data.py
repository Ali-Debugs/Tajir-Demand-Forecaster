"""
generate_data.py
Generates synthetic kiryana store sales data for the Tajir Demand Forecaster.
Run once to create data/sales.csv and data/stores.csv
"""

import pandas as pd
import numpy as np
import os

np.random.seed(42)

STORES = [
    {"store_id": 1, "name": "Ali General Store",    "area": "Gulberg",       "owner": "Muhammad Ali"},
    {"store_id": 2, "name": "Hassan Kiryana",        "area": "Johar Town",    "owner": "Hassan Raza"},
    {"store_id": 3, "name": "Noor Brothers",         "area": "Model Town",    "owner": "Noor Ahmed"},
    {"store_id": 4, "name": "Rehman Trading",        "area": "DHA Phase 5",   "owner": "Abdul Rehman"},
    {"store_id": 5, "name": "Bilal Super Store",     "area": "Bahria Town",   "owner": "Bilal Khan"},
]

PRODUCTS = [
    {"product_id": 1,  "name": "Olpers Milk 1L",        "category": "Dairy",      "unit_price": 85,  "restock_threshold": 20},
    {"product_id": 2,  "name": "Surf Excel 500g",       "category": "Detergent",  "unit_price": 320, "restock_threshold": 15},
    {"product_id": 3,  "name": "Lays Classic (Large)",  "category": "Snacks",     "unit_price": 60,  "restock_threshold": 30},
    {"product_id": 4,  "name": "Tapal Danedar 200g",    "category": "Beverages",  "unit_price": 175, "restock_threshold": 10},
    {"product_id": 5,  "name": "Nestle Mineral Water",  "category": "Beverages",  "unit_price": 50,  "restock_threshold": 40},
    {"product_id": 6,  "name": "Shan Biryani Masala",   "category": "Spices",     "unit_price": 95,  "restock_threshold": 12},
    {"product_id": 7,  "name": "Peak Freans Sooper",    "category": "Biscuits",   "unit_price": 45,  "restock_threshold": 25},
    {"product_id": 8,  "name": "Sunsilk Shampoo 200ml", "category": "Personal",   "unit_price": 220, "restock_threshold": 8},
    {"product_id": 9,  "name": "Colgate 100ml",         "category": "Personal",   "unit_price": 130, "restock_threshold": 10},
    {"product_id": 10, "name": "Cocomo Biscuits",       "category": "Biscuits",   "unit_price": 20,  "restock_threshold": 50},
]

# Base daily demand per product (units/day)
BASE_DEMAND = {1:18, 2:8, 3:22, 4:7, 5:35, 6:6, 7:20, 8:5, 9:7, 10:45}

# Store multipliers (bigger store = more sales)
STORE_MULT = {1:1.3, 2:1.0, 3:1.1, 4:0.9, 5:1.2}

def generate_sales():
    dates = pd.date_range("2024-09-01", "2025-02-28", freq="D")
    records = []

    for store in STORES:
        sid = store["store_id"]
        for prod in PRODUCTS:
            pid = prod["product_id"]
            base = BASE_DEMAND[pid] * STORE_MULT[sid]

            for i, date in enumerate(dates):
                # Weekly seasonality: higher on weekends (Fri/Sat in PK)
                weekday_boost = 1.25 if date.dayofweek in [4, 5] else 1.0

                # Monthly seasonality: Ramadan spike simulation in March
                month_boost = 1.0
                if date.month == 12:   month_boost = 1.1  # winter
                if date.month == 1:    month_boost = 0.9  # slow Jan

                # Trend: slight growth over time
                trend = 1 + (i / len(dates)) * 0.08

                mu = base * weekday_boost * month_boost * trend
                units_sold = max(0, int(np.random.poisson(mu)))

                records.append({
                    "date": date.date(),
                    "store_id": sid,
                    "product_id": pid,
                    "units_sold": units_sold,
                    "revenue": units_sold * prod["unit_price"],
                })

    df = pd.DataFrame(records)
    return df

if __name__ == "__main__":
    os.makedirs("data", exist_ok=True)

    sales_df = generate_sales()
    sales_df.to_csv("data/sales.csv", index=False)

    stores_df = pd.DataFrame(STORES)
    stores_df.to_csv("data/stores.csv", index=False)

    products_df = pd.DataFrame(PRODUCTS)
    products_df.to_csv("data/products.csv", index=False)

    print(f"✅ Generated {len(sales_df):,} sales records")
    print(f"✅ Saved to data/sales.csv, data/stores.csv, data/products.csv")
