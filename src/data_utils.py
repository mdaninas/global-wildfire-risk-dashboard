from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"


SUPPORTED_DATA_EXTENSIONS = (".csv", ".parquet", ".json", ".xlsx", ".xls")

NUMERIC_COLUMNS = [
    "latitude",
    "longitude",
    "brightness",
    "bright_ti4",
    "bright_ti5",
    "bright_t31",
    "frp",
    "scan",
    "track",
    "year",
    "month",
    "day",
]

COLUMN_ALIASES = {
    "lat": "latitude",
    "lon": "longitude",
    "lng": "longitude",
    "long": "longitude",
    "acquisition_date": "acq_date",
    "acquisition_time": "acq_time",
    "date": "acq_date",
    "time": "acq_time",
}

CONFIDENCE_MAP = {
    "l": 33.0,
    "low": 33.0,
    "n": 66.0,
    "nominal": 66.0,
    "m": 66.0,
    "medium": 66.0,
    "h": 100.0,
    "high": 100.0,
}


def standardize_column_name(name: str) -> str:
    """Normalize source column names while preserving expected FIRMS semantics."""
    cleaned = re.sub(r"[^0-9a-zA-Z]+", "_", str(name).strip().lower())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return COLUMN_ALIASES.get(cleaned, cleaned)


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [standardize_column_name(col) for col in df.columns]
    return df


def find_raw_dataset(raw_dir: Path | str = RAW_DIR) -> Path:
    """Find the most relevant raw wildfire dataset in the raw data directory."""
    raw_dir = Path(raw_dir)
    search_dirs = [raw_dir]
    sample_dir = DATA_DIR / "sample"
    if raw_dir.resolve() != sample_dir.resolve():
        search_dirs.append(sample_dir)

    candidates = []
    for directory in search_dirs:
        if not directory.exists():
            continue
        candidates.extend(
            path
            for path in directory.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_DATA_EXTENSIONS
        )
    if not candidates:
        raise FileNotFoundError(
            f"No supported dataset found in {raw_dir} or {sample_dir}. "
            "Place the full FIRMS CSV in data/raw or keep the sample CSV in data/sample."
        )

    def score(path: Path) -> tuple[int, int]:
        name = path.name.lower()
        keyword_score = sum(keyword in name for keyword in ["firm", "fire", "wildfire", "hotspot", "nasa"])
        return keyword_score, path.stat().st_size

    return sorted(candidates, key=score, reverse=True)[0]


def read_dataset(path: Path | str | None = None, nrows: int | None = None) -> pd.DataFrame:
    path = Path(path) if path else find_raw_dataset()
    suffix = path.suffix.lower()

    if suffix == ".csv":
        return pd.read_csv(path, low_memory=False, nrows=nrows)
    if suffix == ".parquet":
        return pd.read_parquet(path)
    if suffix == ".json":
        return pd.read_json(path, lines=True)
    if suffix in {".xlsx", ".xls"}:
        return pd.read_excel(path, nrows=nrows)

    raise ValueError(f"Unsupported dataset format: {path.suffix}")


def parse_acquisition_datetime(df: pd.DataFrame) -> pd.Series:
    """Create a UTC timestamp from FIRMS acquisition date and HHMM time columns."""
    if "acq_date" not in df.columns:
        return pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns, UTC]")

    dates = df["acq_date"].astype("string").str.strip()
    if "acq_time" in df.columns:
        times = (
            df["acq_time"]
            .astype("string")
            .str.replace(r"\.0$", "", regex=True)
            .str.extract(r"(\d+)", expand=False)
            .fillna("")
            .str.zfill(4)
            .str[-4:]
        )
        combined = dates + " " + times
        parsed = pd.to_datetime(combined, format="%Y-%m-%d %H%M", errors="coerce", utc=True)
        fallback_mask = parsed.isna()
        if fallback_mask.any():
            parsed.loc[fallback_mask] = pd.to_datetime(
                combined.loc[fallback_mask], errors="coerce", utc=True
            )
        return parsed

    return pd.to_datetime(dates, errors="coerce", utc=True)


def normalize_confidence(confidence: pd.Series) -> tuple[pd.Series, pd.Series]:
    """Return numeric confidence score and readable confidence label."""
    text = confidence.astype("string").str.strip().str.lower()
    mapped_score = text.map(CONFIDENCE_MAP).astype("float64")
    text_label = text.map(
        {
            "l": "Low",
            "low": "Low",
            "n": "Nominal",
            "nominal": "Nominal",
            "m": "Nominal",
            "medium": "Nominal",
            "h": "High",
            "high": "High",
        }
    ).astype("string")

    numeric = pd.to_numeric(confidence, errors="coerce")
    if numeric.notna().any() and numeric.max(skipna=True) <= 1:
        numeric = numeric * 100
    numeric_score = numeric.clip(lower=0, upper=100)
    numeric_label = pd.cut(
        numeric_score,
        bins=[-0.01, 33.0, 66.0, 100.0],
        labels=["Low", "Nominal", "High"],
        include_lowest=True,
    ).astype("string")

    score = numeric_score.where(numeric_score.notna(), mapped_score)
    label = numeric_label.where(numeric_score.notna(), text_label)
    return score, label.fillna("Unknown")


def add_analysis_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    df["acq_datetime"] = parse_acquisition_datetime(df)
    df["acq_date_clean"] = df["acq_datetime"].dt.date

    if "confidence" in df.columns:
        df["confidence_score"], df["confidence_label"] = normalize_confidence(df["confidence"])
    else:
        df["confidence_score"] = np.nan
        df["confidence_label"] = "Unknown"

    brightness_sources = [
        col for col in ["brightness", "bright_ti4", "bright_t31", "bright_ti5"] if col in df.columns
    ]
    if brightness_sources:
        df["brightness_primary"] = df[brightness_sources].bfill(axis=1).iloc[:, 0]
    else:
        df["brightness_primary"] = np.nan

    if "daynight" in df.columns:
        df["daynight"] = (
            df["daynight"]
            .astype("string")
            .str.strip()
            .replace({"D": "Day", "N": "Night", "d": "Day", "n": "Night", "": "Unknown"})
            .fillna("Unknown")
        )

    for column in ["satellite", "instrument", "source_dataset", "season", "lat_band"]:
        if column in df.columns:
            df[column] = df[column].astype("string").str.strip().replace("", "Unknown").fillna("Unknown")

    if df["acq_datetime"].notna().any():
        df["year"] = df["acq_datetime"].dt.year
        df["month"] = df["acq_datetime"].dt.month
        df["day"] = df["acq_datetime"].dt.day
        df["week"] = df["acq_datetime"].dt.isocalendar().week.astype("int64")

    return df


def clean_wildfire_data(raw_path: Path | str | None = None) -> tuple[pd.DataFrame, dict[str, int]]:
    raw_df = read_dataset(raw_path)
    profile = {"raw_rows": len(raw_df), "raw_columns": len(raw_df.columns)}

    df = standardize_columns(raw_df)
    df = add_analysis_columns(df)

    valid_coordinates = (
        df["latitude"].between(-90, 90, inclusive="both")
        & df["longitude"].between(-180, 180, inclusive="both")
    )
    valid_datetime = df["acq_datetime"].notna()
    df = df.loc[valid_coordinates & valid_datetime].copy()

    before_duplicates = len(df)
    df = df.drop_duplicates().reset_index(drop=True)

    profile.update(
        {
            "rows_after_coordinate_datetime_validation": len(df),
            "duplicate_rows_removed": before_duplicates - len(df),
            "final_rows": len(df),
            "final_columns": len(df.columns),
        }
    )
    return df, profile


def save_cleaned_data(
    df: pd.DataFrame,
    output_path: Path | str = PROCESSED_DIR / "cleaned_wildfire_data.csv",
) -> Path:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    return output_path


def load_cleaned_data(
    path: Path | str = PROCESSED_DIR / "cleaned_wildfire_data.csv",
) -> pd.DataFrame:
    path = Path(path)
    df = pd.read_csv(path, low_memory=False)
    if "acq_datetime" in df.columns:
        df["acq_datetime"] = pd.to_datetime(df["acq_datetime"], errors="coerce", utc=True)
    if "acq_date_clean" in df.columns:
        df["acq_date_clean"] = pd.to_datetime(df["acq_date_clean"], errors="coerce").dt.date
    return df


def build_cleaned_dataset(
    raw_path: Path | str | None = None,
    output_path: Path | str = PROCESSED_DIR / "cleaned_wildfire_data.csv",
) -> tuple[pd.DataFrame, dict[str, int], Path]:
    df, profile = clean_wildfire_data(raw_path)
    saved_path = save_cleaned_data(df, output_path)
    return df, profile, saved_path


def available_columns(df: pd.DataFrame, columns: Iterable[str]) -> list[str]:
    return [column for column in columns if column in df.columns and df[column].notna().any()]
