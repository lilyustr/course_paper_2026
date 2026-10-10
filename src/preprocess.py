"""
Preprocess Citi Bike trip data into hourly station-level demand.

Reads the raw Jersey City trip CSV, aggregates trips to one row per
station-hour, engineers calendar and lag features, and writes
``data/processed_hourly.csv``.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

# Project root: parent of ``src/``.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_CSV_PATH = PROJECT_ROOT / "data" / "JC-202609-citibike-tripdata.csv"
OUTPUT_CSV_PATH = PROJECT_ROOT / "data" / "processed_hourly.csv"

REQUIRED_COLUMNS = [
    "started_at",
    "start_station_id",
    "start_station_name",
    "start_lat",
    "start_lng",
]


def load_raw_trips(path: Path) -> pd.DataFrame:
    """Load the raw Citi Bike trip file and keep columns needed for aggregation."""
    df = pd.read_csv(path, usecols=REQUIRED_COLUMNS)
    return df


def clean_trips(df: pd.DataFrame) -> pd.DataFrame:
    """Parse timestamps and drop trips with missing station identity or coordinates."""
    df = df.copy()
    df["started_at"] = pd.to_datetime(df["started_at"], errors="coerce")
    df = df.dropna(subset=["started_at", "start_station_id", "start_lat", "start_lng"])
    return df


def aggregate_hourly(df: pd.DataFrame) -> pd.DataFrame:
    """
    Count trips per station per hour.

    ``started_at`` is floored to the hour. Latitude and longitude are averaged
    within each station-hour so GPS jitter does not split a station into
    multiple groups, while still producing spatial columns for mapping.
    """
    df = df.copy()
    df["hour"] = df["started_at"].dt.floor("h")

    hourly = (
        df.groupby(["start_station_id", "start_station_name", "hour"], as_index=False)
        .agg(
            start_lat=("start_lat", "mean"),
            start_lng=("start_lng", "mean"),
            trip_count=("started_at", "size"),
        )
    )
    return hourly


def add_time_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add calendar features derived from the hourly timestamp."""
    df = df.copy()
    df["hour_of_day"] = df["hour"].dt.hour
    df["day_of_week"] = df["hour"].dt.dayofweek
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    return df


def add_lag_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add ``lag_1h``: trip count at the same station one hour earlier.

    Rows with no matching previous hour (first hour of a station, or a gap
    with zero demand) are filled with 0.
    """
    df = df.copy()

    lag = df[["start_station_id", "hour", "trip_count"]].rename(
        columns={"trip_count": "lag_1h"}
    )
    lag["hour"] = lag["hour"] + pd.Timedelta(hours=1)

    df = df.merge(lag, on=["start_station_id", "hour"], how="left")
    df["lag_1h"] = df["lag_1h"].fillna(0).astype(int)
    return df


def preprocess(
    raw_path: Path = RAW_CSV_PATH,
    output_path: Path = OUTPUT_CSV_PATH,
) -> pd.DataFrame:
    """Run the full pipeline and persist the hourly feature table."""
    trips = load_raw_trips(raw_path)
    trips = clean_trips(trips)
    hourly = aggregate_hourly(trips)
    hourly = add_time_features(hourly)
    hourly = add_lag_features(hourly)

    hourly = hourly.sort_values(["start_station_id", "hour"]).reset_index(drop=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    hourly.to_csv(output_path, index=False)
    return hourly


if __name__ == "__main__":
    processed = preprocess()
    print(f"Saved hourly dataset to: {OUTPUT_CSV_PATH}")
    print(f"Shape: {processed.shape}")
    print(processed.head())
