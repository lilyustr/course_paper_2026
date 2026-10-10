"""
FastAPI service for Citi Bike station demand prediction.

Loads the trained Random Forest pipeline and hourly history at startup,
then exposes station metadata and one-hour-ahead demand forecasts with
rebalancing guidance.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODEL_PATH = PROJECT_ROOT / "models" / "rf_demand_model.joblib"
DATA_PATH = PROJECT_ROOT / "data" / "processed_hourly.csv"

FEATURE_COLUMNS = [
    "hour_of_day",
    "day_of_week",
    "is_weekend",
    "lag_1h",
    "start_lat",
    "start_lng",
]

# Module-level artifacts populated in lifespan.
model = None
hourly_df: pd.DataFrame | None = None
stations_df: pd.DataFrame | None = None
station_quantiles: pd.DataFrame | None = None


class PredictRequest(BaseModel):
    station_id: str = Field(..., description="Citi Bike start_station_id, e.g. JC102")
    target_time: Optional[str] = Field(
        default=None,
        description="ISO datetime for the forecast hour. Defaults to now if omitted.",
    )


class StationOut(BaseModel):
    start_station_id: str
    start_station_name: str
    start_lat: float
    start_lng: float


class PredictResponse(BaseModel):
    station_id: str
    station_name: str
    start_lat: float
    start_lng: float
    target_time: str
    forecast_hour: str
    lag_1h: int
    predicted_trip_count: float
    risk_status: str
    operational_risk: str
    rebalancing_suggestion: str


def load_artifacts() -> tuple[object, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Load the model, hourly history, station catalog, and demand quantiles."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"Trained model not found: {MODEL_PATH}")
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Processed dataset not found: {DATA_PATH}")

    loaded_model = joblib.load(MODEL_PATH)
    hourly = pd.read_csv(DATA_PATH, parse_dates=["hour"])
    hourly["start_station_id"] = hourly["start_station_id"].astype(str)

    stations = (
        hourly.sort_values("hour")
        .groupby("start_station_id", as_index=False)
        .agg(
            start_station_name=("start_station_name", "last"),
            start_lat=("start_lat", "last"),
            start_lng=("start_lng", "last"),
        )
        .sort_values("start_station_name")
        .reset_index(drop=True)
    )

    quantiles = (
        hourly.groupby("start_station_id")["trip_count"]
        .quantile([0.25, 0.75])
        .unstack()
        .rename(columns={0.25: "q25", 0.75: "q75"})
        .reset_index()
    )
    return loaded_model, hourly, stations, quantiles


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, hourly_df, stations_df, station_quantiles
    model, hourly_df, stations_df, station_quantiles = load_artifacts()
    yield


app = FastAPI(
    title="Bike Demand Prediction API",
    description="Spatio-temporal Citi Bike demand forecasts for rebalancing decisions.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def parse_target_time(value: Optional[str]) -> datetime:
    """Parse an optional ISO timestamp; default to the current local time."""
    if value is None or value.strip() == "":
        return datetime.now()
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail="target_time must be a valid ISO datetime string.",
        ) from exc


def get_station_row(station_id: str) -> pd.Series:
    assert stations_df is not None
    match = stations_df[stations_df["start_station_id"] == str(station_id)]
    if match.empty:
        raise HTTPException(status_code=404, detail=f"Unknown station_id: {station_id}")
    return match.iloc[0]


def get_lag_1h(station_id: str, forecast_hour: pd.Timestamp) -> int:
    """
    Trip count at this station one hour before the forecast hour.

    If that exact hour is missing (common when querying 'now' after the
    dataset window), fall back to the most recent observed hour before
    the forecast, otherwise 0.
    """
    assert hourly_df is not None
    previous_hour = forecast_hour - pd.Timedelta(hours=1)
    station_history = hourly_df[hourly_df["start_station_id"] == str(station_id)]

    exact = station_history[station_history["hour"] == previous_hour]
    if not exact.empty:
        return int(exact.iloc[0]["trip_count"])

    earlier = station_history[station_history["hour"] < forecast_hour].sort_values("hour")
    if not earlier.empty:
        return int(earlier.iloc[-1]["trip_count"])
    return 0


def classify_risk(station_id: str, predicted: float) -> tuple[str, str, str]:
    """
    Map predicted outbound demand to risk and a rebalancing action.

    High start-trip demand empties docks of bikes (shortage).
    Low demand leaves bikes unused and can fill docks (overflow).
    """
    assert station_quantiles is not None
    qrow = station_quantiles[station_quantiles["start_station_id"] == str(station_id)]
    q25 = float(qrow.iloc[0]["q25"]) if not qrow.empty else 1.0
    q75 = float(qrow.iloc[0]["q75"]) if not qrow.empty else 4.0

    if predicted >= q75:
        return (
            "HIGH_DEMAND",
            "SHORTAGE_RISK",
            "High outbound demand expected. Deliver additional bikes to this station to avoid empty docks.",
        )
    if predicted <= q25:
        return (
            "LOW_DEMAND",
            "OVERFLOW_RISK",
            "Low outbound demand expected. Remove surplus bikes from this station to free docks for incoming trips.",
        )
    return (
        "NORMAL",
        "NONE",
        "Demand is within the typical range. No rebalancing is required this hour.",
    )


@app.get("/")
def health_check() -> dict[str, str]:
    return {"status": "ok", "message": "Bike Demand Prediction API"}


@app.get("/api/stations", response_model=list[StationOut])
def list_stations() -> list[dict]:
    if stations_df is None:
        raise HTTPException(status_code=503, detail="Station catalog is not loaded yet.")
    return stations_df.to_dict(orient="records")


@app.post("/api/predict", response_model=PredictResponse)
def predict_demand(payload: PredictRequest) -> PredictResponse:
    if model is None or hourly_df is None:
        raise HTTPException(status_code=503, detail="Model artifacts are not loaded yet.")

    station = get_station_row(payload.station_id)
    target_dt = parse_target_time(payload.target_time)
    forecast_hour = pd.Timestamp(target_dt).floor("h")

    hour_of_day = int(forecast_hour.hour)
    day_of_week = int(forecast_hour.dayofweek)
    is_weekend = int(day_of_week >= 5)
    lag_1h = get_lag_1h(str(station["start_station_id"]), forecast_hour)

    features = pd.DataFrame(
        [
            {
                "hour_of_day": hour_of_day,
                "day_of_week": day_of_week,
                "is_weekend": is_weekend,
                "lag_1h": lag_1h,
                "start_lat": float(station["start_lat"]),
                "start_lng": float(station["start_lng"]),
            }
        ],
        columns=FEATURE_COLUMNS,
    )

    predicted = float(max(0.0, model.predict(features)[0]))
    risk_status, operational_risk, suggestion = classify_risk(
        str(station["start_station_id"]), predicted
    )

    return PredictResponse(
        station_id=str(station["start_station_id"]),
        station_name=str(station["start_station_name"]),
        start_lat=float(station["start_lat"]),
        start_lng=float(station["start_lng"]),
        target_time=target_dt.isoformat(),
        forecast_hour=forecast_hour.isoformat(),
        lag_1h=lag_1h,
        predicted_trip_count=round(predicted, 2),
        risk_status=risk_status,
        operational_risk=operational_risk,
        rebalancing_suggestion=suggestion,
    )
