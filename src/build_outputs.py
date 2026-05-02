from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from data_utils import build_cleaned_dataset, find_raw_dataset
from risk_model import build_and_save_risk_scores


def main() -> None:
    raw_path = find_raw_dataset(ROOT_DIR / "data" / "raw")
    clean_path = ROOT_DIR / "data" / "processed" / "cleaned_wildfire_data.csv"
    risk_path = ROOT_DIR / "data" / "processed" / "wildfire_risk_scores.csv"
    report_path = ROOT_DIR / "reports" / "data_profile.json"

    clean_df, profile, saved_clean = build_cleaned_dataset(raw_path, clean_path)
    risk_df, saved_risk = build_and_save_risk_scores(clean_df, risk_path, grid_size=1.0)

    peak_days = (
        clean_df.assign(date=clean_df["acq_datetime"].dt.date)
        .groupby("date")
        .size()
        .sort_values(ascending=False)
        .head(5)
        .rename("detections")
        .reset_index()
    )
    peak_days["date"] = peak_days["date"].astype("string")

    summary = {
        "raw_path": str(raw_path.relative_to(ROOT_DIR)),
        "cleaned_path": str(saved_clean.relative_to(ROOT_DIR)),
        "risk_path": str(saved_risk.relative_to(ROOT_DIR)),
        "profile": profile,
        "date_min": str(clean_df["acq_datetime"].min()),
        "date_max": str(clean_df["acq_datetime"].max()),
        "satellite_counts": clean_df["satellite"].value_counts().head(8).to_dict()
        if "satellite" in clean_df
        else {},
        "instrument_counts": clean_df["instrument"].value_counts().head(8).to_dict()
        if "instrument" in clean_df
        else {},
        "daynight_counts": clean_df["daynight"].value_counts().to_dict()
        if "daynight" in clean_df
        else {},
        "confidence_counts": clean_df["confidence_label"].value_counts().to_dict()
        if "confidence_label" in clean_df
        else {},
        "top_lat_band": clean_df["lat_band"].value_counts().head(8).to_dict()
        if "lat_band" in clean_df
        else {},
        "peak_days": peak_days.to_dict(orient="records"),
        "risk_category_counts": risk_df["risk_category"].value_counts().to_dict(),
        "top_risk": risk_df[
            [
                "grid_label",
                "risk_score",
                "risk_category",
                "hotspot_count",
                "avg_frp",
                "avg_brightness",
                "avg_confidence",
                "latest_detection",
            ]
        ]
        .head(10)
        .to_dict(orient="records"),
    }

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
