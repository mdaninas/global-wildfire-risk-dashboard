from __future__ import annotations

import numpy as np
import pandas as pd


def add_grid_columns(df: pd.DataFrame, grid_size: float = 1.0) -> pd.DataFrame:
    """Assign each detection to a latitude-longitude grid cell."""
    if grid_size <= 0:
        raise ValueError("grid_size must be greater than 0")

    required = {"latitude", "longitude"}
    missing = required.difference(df.columns)
    if missing:
        raise KeyError(f"Missing coordinate columns: {sorted(missing)}")

    output = df.copy()
    output["lat_bin"] = np.floor(output["latitude"] / grid_size) * grid_size
    output["lon_bin"] = np.floor(output["longitude"] / grid_size) * grid_size
    output["grid_center_lat"] = output["lat_bin"] + grid_size / 2
    output["grid_center_lon"] = output["lon_bin"] + grid_size / 2
    output["grid_id"] = (
        "lat_"
        + output["lat_bin"].round(2).map(lambda value: f"{value:+.2f}")
        + "_lon_"
        + output["lon_bin"].round(2).map(lambda value: f"{value:+.2f}")
    )
    output["grid_label"] = (
        output["lat_bin"].round(2).astype("string")
        + " to "
        + (output["lat_bin"] + grid_size).round(2).astype("string")
        + " lat, "
        + output["lon_bin"].round(2).astype("string")
        + " to "
        + (output["lon_bin"] + grid_size).round(2).astype("string")
        + " lon"
    )
    return output


def _mode_or_unknown(series: pd.Series) -> str:
    values = series.dropna()
    if values.empty:
        return "Unknown"
    return str(values.mode().iloc[0])


def aggregate_grid_metrics(df: pd.DataFrame, grid_size: float = 1.0) -> pd.DataFrame:
    """Aggregate wildfire activity into grid-level metrics for ranking and scoring."""
    grid_df = add_grid_columns(df, grid_size=grid_size)

    aggregation: dict[str, tuple[str, str]] = {
        "hotspot_count": ("latitude", "size"),
        "center_lat": ("grid_center_lat", "first"),
        "center_lon": ("grid_center_lon", "first"),
        "grid_label": ("grid_label", "first"),
    }

    optional_metrics = {
        "frp": [("avg_frp", "mean"), ("max_frp", "max"), ("total_frp", "sum")],
        "brightness_primary": [("avg_brightness", "mean"), ("max_brightness", "max")],
        "confidence_score": [("avg_confidence", "mean")],
        "acq_datetime": [("latest_detection", "max")],
        "acq_date_clean": [("active_days", "nunique")],
    }

    for source_column, metrics in optional_metrics.items():
        if source_column in grid_df.columns:
            for output_column, function_name in metrics:
                aggregation[output_column] = (source_column, function_name)

    grouped = grid_df.groupby(["grid_id", "lat_bin", "lon_bin"], dropna=False).agg(**aggregation)
    grouped = grouped.reset_index()

    for column in ["satellite", "instrument", "daynight", "season", "lat_band"]:
        if column in grid_df.columns:
            grouped[f"dominant_{column}"] = (
                grid_df.groupby(["grid_id", "lat_bin", "lon_bin"], dropna=False)[column]
                .agg(_mode_or_unknown)
                .to_numpy()
            )

    return grouped.sort_values("hotspot_count", ascending=False).reset_index(drop=True)


def daily_trend(df: pd.DataFrame) -> pd.DataFrame:
    if "acq_datetime" not in df.columns:
        raise KeyError("acq_datetime column is required for daily trends")
    trend = (
        df.assign(date=pd.to_datetime(df["acq_datetime"], utc=True).dt.date)
        .groupby("date", as_index=False)
        .agg(fire_detections=("latitude", "size"))
    )
    return trend.sort_values("date")


def monthly_trend(df: pd.DataFrame) -> pd.DataFrame:
    if "acq_datetime" not in df.columns:
        raise KeyError("acq_datetime column is required for monthly trends")
    trend = (
        df.assign(month=pd.to_datetime(df["acq_datetime"], utc=True).dt.to_period("M").astype("string"))
        .groupby("month", as_index=False)
        .agg(fire_detections=("latitude", "size"))
    )
    return trend.sort_values("month")


def sample_for_map(
    df: pd.DataFrame,
    max_points: int = 12_000,
    random_state: int = 42,
) -> pd.DataFrame:
    """Keep maps responsive by sampling points while preserving full-data aggregations elsewhere."""
    if len(df) <= max_points:
        return df.copy()

    sort_columns = [column for column in ["frp", "brightness_primary", "confidence_score"] if column in df.columns]
    if sort_columns:
        high_signal = df.sort_values(sort_columns, ascending=False).head(max_points // 3)
        remaining = df.drop(index=high_signal.index)
        random_sample = remaining.sample(max_points - len(high_signal), random_state=random_state)
        return pd.concat([high_signal, random_sample], ignore_index=True)

    return df.sample(max_points, random_state=random_state).reset_index(drop=True)
