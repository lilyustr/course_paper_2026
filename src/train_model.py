"""
Train a station-hour bike demand regressor and evaluate baseline models.

Loads ``data/processed_hourly.csv``, fits baseline models and a Random Forest pipeline
on a chronological train/test split, prints a comparison table (MAE / RMSE / R²),
and saves the main sklearn pipeline to ``models/rf_demand_model.joblib``.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "processed_hourly.csv"
MODEL_PATH = PROJECT_ROOT / "models" / "rf_demand_model.joblib"

FEATURE_COLUMNS = [
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "lag_1h",
    "start_lat",
    "start_lng",
]
TARGET_COLUMN = "trip_count"
TIME_COLUMN = "hour"
STATION_COLUMN = "start_station_id"
TRAIN_FRACTION = 0.80
RANDOM_STATE = 42


def load_hourly_data(path: Path) -> pd.DataFrame:
    """Load the preprocessed hourly demand table."""
    df = pd.read_csv(path, parse_dates=[TIME_COLUMN])
    missing = [col for col in FEATURE_COLUMNS + [TARGET_COLUMN, TIME_COLUMN] if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in {path}: {missing}")
    return df.dropna(subset=FEATURE_COLUMNS + [TARGET_COLUMN, TIME_COLUMN])


def chronological_split(
    df: pd.DataFrame,
    train_fraction: float = TRAIN_FRACTION,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split by time, not by random rows.

    Hours are sorted; the earliest ``train_fraction`` of unique timestamps
    become the training window so later hours stay in the test set.
    """
    df = df.sort_values([TIME_COLUMN, STATION_COLUMN]).reset_index(drop=True)
    unique_hours = np.sort(df[TIME_COLUMN].unique())
    cutoff_index = max(1, int(len(unique_hours) * train_fraction))
    cutoff_hour = unique_hours[min(cutoff_index, len(unique_hours) - 1)]

    train_df = df[df[TIME_COLUMN] < cutoff_hour].copy()
    test_df = df[df[TIME_COLUMN] >= cutoff_hour].copy()

    if train_df.empty or test_df.empty:
        raise ValueError("Chronological split produced an empty train or test set.")
    return train_df, test_df


def build_rf_pipeline() -> Pipeline:
    """Random Forest pipeline."""
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=16,
        min_samples_leaf=2,
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )
    return Pipeline([("regressor", model)])


def evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Compute regression metrics."""
    mae = mean_absolute_error(y_true, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = r2_score(y_true, y_pred)
    return {"MAE": mae, "RMSE": rmse, "R2": r2}


def train_and_evaluate_all(
    data_path: Path = DATA_PATH,
    model_path: Path = MODEL_PATH,
) -> tuple[Pipeline, dict[str, dict[str, float]], pd.DataFrame, pd.DataFrame]:
    """Fit baseline and main models, report metrics table, and save main pipeline."""
    df = load_hourly_data(data_path)
    train_df, test_df = chronological_split(df)

    X_train = train_df[FEATURE_COLUMNS]
    y_train = train_df[TARGET_COLUMN]
    X_test = test_df[FEATURE_COLUMNS]
    y_test = test_df[TARGET_COLUMN]

    all_metrics: dict[str, dict[str, float]] = {}

    # --- BASELINE 1: Historical Average ---
    hist_group = train_df.groupby([STATION_COLUMN, "hour_of_day", "day_of_week"])[TARGET_COLUMN].mean().reset_index()
    hist_group.rename(columns={TARGET_COLUMN: "pred_hist"}, inplace=True)
    test_merged = test_df.merge(hist_group, on=[STATION_COLUMN, "hour_of_day", "day_of_week"], how="left")
    y_pred_hist = test_merged["pred_hist"].fillna(y_train.mean()).to_numpy()
    all_metrics["Historical Average"] = evaluate(y_test.to_numpy(), y_pred_hist)

    # --- BASELINE 2: Naive Lag (1h) ---
    y_pred_naive = test_df["lag_1h"].to_numpy()
    all_metrics["Naive Lag (1h)"] = evaluate(y_test.to_numpy(), y_pred_naive)

    # --- BASELINE 3: Linear Regression ---
    lr_model = LinearRegression()
    lr_model.fit(X_train, y_train)
    y_pred_lr = lr_model.predict(X_test)
    all_metrics["Linear Regression"] = evaluate(y_test.to_numpy(), y_pred_lr)

    # --- MAIN MODEL: Random Forest Pipeline ---
    rf_pipeline = build_rf_pipeline()
    rf_pipeline.fit(X_train, y_train)
    y_pred_rf = rf_pipeline.predict(X_test)
    all_metrics["Random Forest (Main)"] = evaluate(y_test.to_numpy(), y_pred_rf)

    # Save Random Forest Pipeline
    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(rf_pipeline, model_path)

    return rf_pipeline, all_metrics, train_df, test_df


if __name__ == "__main__":
    _, all_metrics, train_df, test_df = train_and_evaluate_all()
    
    print(f"Train rows: {len(train_df):,} | Test rows: {len(test_df):,}")
    print(f"Train hours: {train_df[TIME_COLUMN].min()} → {train_df[TIME_COLUMN].max()}")
    print(f"Test hours:  {test_df[TIME_COLUMN].min()} → {test_df[TIME_COLUMN].max()}\n")

    print("=" * 55)
    print(f"{'Model / Baseline':<22} | {'MAE':<7} | {'RMSE':<7} | {'R²':<7}")
    print("=" * 55)
    for model_name, m in all_metrics.items():
        print(f"{model_name:<22} | {m['MAE']:.4f}  | {m['RMSE']:.4f}  | {m['R2']:.4f}")
    print("=" * 55 + "\n")

    print(f"Saved best model pipeline to: {MODEL_PATH}")