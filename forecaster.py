"""
forecaster.py
Demand forecasting using linear regression with time/seasonal features.
Returns 7-day ahead predictions per product per store.
"""

import pandas as pd
import numpy as np
from sklearn.linear_model import Ridge
from sklearn.preprocessing import StandardScaler


def make_features(df: pd.DataFrame) -> pd.DataFrame:
    """Build time-series features from a daily sales dataframe."""
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    df["day_of_week"]  = df["date"].dt.dayofweek
    df["day_of_month"] = df["date"].dt.day
    df["month"]        = df["date"].dt.month
    df["day_index"]    = (df["date"] - df["date"].min()).dt.days

    # Lag features
    df["lag_1"] = df["units_sold"].shift(1)
    df["lag_7"] = df["units_sold"].shift(7)
    df["rolling_7_mean"] = df["units_sold"].shift(1).rolling(7).mean()
    df["rolling_7_std"]  = df["units_sold"].shift(1).rolling(7).std().fillna(0)

    return df.dropna()


def train_and_forecast(store_id: int, product_id: int,
                       sales_df: pd.DataFrame, horizon: int = 7):
    """
    Train a Ridge regression model on historical sales and return
    a forecast DataFrame with columns: date, predicted_units.
    """
    subset = sales_df[
        (sales_df["store_id"] == store_id) &
        (sales_df["product_id"] == product_id)
    ][["date", "units_sold"]].copy()

    if len(subset) < 30:
        return None

    feat_df = make_features(subset)

    FEATURES = ["day_of_week", "day_of_month", "month",
                "day_index", "lag_1", "lag_7",
                "rolling_7_mean", "rolling_7_std"]

    X = feat_df[FEATURES].values
    y = feat_df["units_sold"].values

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    model = Ridge(alpha=1.0)
    model.fit(X_scaled, y)

    # Build future rows iteratively
    last_date   = pd.to_datetime(feat_df["date"].max())
    last_idx    = int(feat_df["day_index"].max())
    history     = list(feat_df["units_sold"].values)
    min_date    = pd.to_datetime(feat_df["date"].min())

    forecasts = []
    for i in range(1, horizon + 1):
        future_date = last_date + pd.Timedelta(days=i)
        row = {
            "day_of_week":    future_date.dayofweek,
            "day_of_month":   future_date.day,
            "month":          future_date.month,
            "day_index":      last_idx + i,
            "lag_1":          history[-1],
            "lag_7":          history[-7] if len(history) >= 7 else np.mean(history),
            "rolling_7_mean": np.mean(history[-7:]),
            "rolling_7_std":  np.std(history[-7:]),
        }
        x_row = scaler.transform([[row[f] for f in FEATURES]])
        pred  = max(0, model.predict(x_row)[0])
        history.append(pred)
        forecasts.append({"date": future_date.date(), "predicted_units": round(pred, 1)})

    return pd.DataFrame(forecasts)


def get_restock_alerts(store_id: int, sales_df: pd.DataFrame,
                       products_df: pd.DataFrame, horizon: int = 7):
    """
    Returns a list of dicts with restock urgency for each product.
    """
    alerts = []
    for _, prod in products_df.iterrows():
        pid       = int(prod["product_id"])
        threshold = int(prod["restock_threshold"])

        fc = train_and_forecast(store_id, pid, sales_df, horizon)
        if fc is None:
            continue

        total_demand  = fc["predicted_units"].sum()
        days_to_empty = threshold / (total_demand / horizon) if total_demand > 0 else 999

        urgency = "🔴 Critical" if days_to_empty < 2 else \
                  "🟠 Soon"     if days_to_empty < 4 else \
                  "🟢 OK"

        alerts.append({
            "product_id":      pid,
            "product_name":    prod["name"],
            "category":        prod["category"],
            "forecast_7d":     round(total_demand, 0),
            "daily_avg":       round(total_demand / horizon, 1),
            "days_to_empty":   round(days_to_empty, 1),
            "restock_urgency": urgency,
            "forecast_df":     fc,
        })

    alerts.sort(key=lambda x: x["days_to_empty"])
    return alerts
