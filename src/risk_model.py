from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from geo_utils import aggregate_grid_metrics


DEFAULT_WEIGHTS = {
    "hotspot_density_score": 0.35,
    "frp_score": 0.20,
    "brightness_score": 0.15,
    "confidence_score_component": 0.15,
    "recent_activity_score": 0.15,
}


def _minmax(series: pd.Series, log_transform: bool = False) -> pd.Series:
    values = pd.to_numeric(series, errors="coerce")
    if log_transform:
        values = np.log1p(values.clip(lower=0))

    if values.notna().sum() == 0:
        return pd.Series(np.nan, index=series.index, dtype="float64")

    min_value = values.min(skipna=True)
    max_value = values.max(skipna=True)
    if pd.isna(min_value) or pd.isna(max_value) or min_value == max_value:
        return pd.Series(1.0, index=series.index, dtype="float64")

    return ((values - min_value) / (max_value - min_value)).clip(0, 1)


def _recent_activity_score(latest_detection: pd.Series) -> pd.Series:
    dates = pd.to_datetime(latest_detection, errors="coerce", utc=True)
    if dates.notna().sum() == 0:
        return pd.Series(np.nan, index=latest_detection.index, dtype="float64")

    max_date = dates.max()
    days_since = (max_date - dates).dt.total_seconds() / 86_400
    return np.exp(-days_since / 30).clip(0, 1)


def _weighted_score(metrics: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    score = pd.Series(0.0, index=metrics.index)
    total_weight = pd.Series(0.0, index=metrics.index)

    for column, weight in weights.items():
        if column not in metrics.columns:
            continue
        values = metrics[column]
        valid = values.notna()
        score.loc[valid] += values.loc[valid] * weight
        total_weight.loc[valid] += weight

    total_weight = total_weight.replace(0, np.nan)
    return (score / total_weight * 100).fillna(0).clip(0, 100)


def assign_risk_category(score: pd.Series) -> pd.Series:
    score = pd.to_numeric(score, errors="coerce")
    categories = np.select(
        [
            score <= 25,
            score <= 50,
            score < 76,
            score <= 100,
        ],
        ["Low", "Medium", "High", "Critical"],
        default="Unknown",
    )
    return pd.Series(categories, index=score.index, dtype="string")


def compute_risk_scores(
    df: pd.DataFrame,
    grid_size: float = 1.0,
    weights: dict[str, float] | None = None,
) -> pd.DataFrame:
    """Compute a 0-100 wildfire risk score for each grid cell."""
    weights = weights or DEFAULT_WEIGHTS
    grid_metrics = aggregate_grid_metrics(df, grid_size=grid_size)

    grid_metrics["hotspot_density_score"] = _minmax(grid_metrics["hotspot_count"], log_transform=True)

    if "avg_frp" in grid_metrics.columns:
        grid_metrics["frp_score"] = _minmax(grid_metrics["avg_frp"], log_transform=True)
    if "avg_brightness" in grid_metrics.columns:
        grid_metrics["brightness_score"] = _minmax(grid_metrics["avg_brightness"])
    if "avg_confidence" in grid_metrics.columns:
        grid_metrics["confidence_score_component"] = (grid_metrics["avg_confidence"] / 100).clip(0, 1)
    if "latest_detection" in grid_metrics.columns:
        grid_metrics["recent_activity_score"] = _recent_activity_score(grid_metrics["latest_detection"])

    grid_metrics["risk_score"] = _weighted_score(grid_metrics, weights).round(2)
    grid_metrics["risk_category"] = assign_risk_category(grid_metrics["risk_score"])

    return grid_metrics.sort_values("risk_score", ascending=False).reset_index(drop=True)


def save_risk_scores(
    risk_scores: pd.DataFrame,
    output_path: Path | str,
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    risk_scores.to_csv(output_path, index=False)
    return output_path


def build_and_save_risk_scores(
    df: pd.DataFrame,
    output_path: Path | str,
    grid_size: float = 1.0,
) -> tuple[pd.DataFrame, Path]:
    risk_scores = compute_risk_scores(df, grid_size=grid_size)
    saved_path = save_risk_scores(risk_scores, output_path)
    return risk_scores, saved_path
