"""
Train a station-hour bike demand regressor.

Loads ``data/processed_hourly.csv``, fits a Random Forest on a chronological
train/test split, prints MAE / RMSE / R², and saves the sklearn pipeline to
``models/rf_demand_model.joblib``.
"""

from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
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
    become the training window so later hours (and all stations in those
    hours) stay in the test set. This avoids leakage from the future.
    """
    df = df.sort_values([TIME_COLUMN, "start_station_id"]).reset_index(drop=True)
    unique_hours = np.sort(df[TIME_COLUMN].unique())
    cutoff_index = max(1, int(len(unique_hours) * train_fraction))
    cutoff_hour = unique_hours[min(cutoff_index, len(unique_hours) - 1)]

    train_df = df[df[TIME_COLUMN] < cutoff_hour].copy()
    test_df = df[df[TIME_COLUMN] >= cutoff_hour].copy()

    if train_df.empty or test_df.empty:
        raise ValueError(
            "Chronological split produced an empty train or test set. "
            "Check that the dataset covers more than one hour."
        )
    return train_df, test_df


def build_pipeline() -> Pipeline:
    """Random Forest pipeline (ready to add preprocessing steps later)."""
    model = RandomForestRegressor(
        n_estimators=200,
        max_depth=16,
        min_samples_leaf=2,
        n_jobs=-1,
        random_state=RANDOM_STATE,
    )
    return Pipeline([("regressor", model)])


def evaluate(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Compute standard regression metrics on the test set."""
    mae = mean_absolute_error(y_true, y_pred)
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = r2_score(y_true, y_pred)
    return {"MAE": mae, "RMSE": rmse, "R2": r2}


def train(
    data_path: Path = DATA_PATH,
    model_path: Path = MODEL_PATH,
) -> tuple[Pipeline, dict[str, float], pd.DataFrame, pd.DataFrame]:
    """Fit the model, report test metrics, and persist the pipeline."""
    df = load_hourly_data(data_path)
    train_df, test_df = chronological_split(df)

    X_train = train_df[FEATURE_COLUMNS]
    y_train = train_df[TARGET_COLUMN]
    X_test = test_df[FEATURE_COLUMNS]
    y_test = test_df[TARGET_COLUMN]

    pipeline = build_pipeline()
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    metrics = evaluate(y_test.to_numpy(), y_pred)

    model_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, model_path)
    return pipeline, metrics, train_df, test_df


if __name__ == "__main__":
    _, metrics, train_df, test_df = train()
    print(f"Train rows: {len(train_df):,} | Test rows: {len(test_df):,}")
    print(f"Train hours: {train_df[TIME_COLUMN].min()} → {train_df[TIME_COLUMN].max()}")
    print(f"Test hours:  {test_df[TIME_COLUMN].min()} → {test_df[TIME_COLUMN].max()}")
    print(f"MAE:  {metrics['MAE']:.4f}")
    print(f"RMSE: {metrics['RMSE']:.4f}")
    print(f"R²:   {metrics['R2']:.4f}")
    print(f"Saved model to: {MODEL_PATH}")
