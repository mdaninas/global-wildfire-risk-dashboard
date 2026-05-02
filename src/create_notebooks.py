from __future__ import annotations

import textwrap
from pathlib import Path

import nbformat as nbf


ROOT_DIR = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = ROOT_DIR / "notebooks"


def markdown(text: str):
    return nbf.v4.new_markdown_cell(textwrap.dedent(text).strip())


def code(text: str):
    return nbf.v4.new_code_cell(textwrap.dedent(text).strip())


def write_notebook(path: Path, cells: list) -> None:
    notebook = nbf.v4.new_notebook()
    notebook["cells"] = cells
    notebook["metadata"] = {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "pygments_lexer": "ipython3"},
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    nbf.write(notebook, path)


def build_data_cleaning() -> list:
    return [
        markdown(
            """
            # 01 - Data Understanding and Cleaning

            This notebook inspects the raw NASA FIRMS multi-sensor wildfire detections dataset, standardizes
            the schema, validates coordinates and timestamps, normalizes confidence values, and writes the
            cleaned analytical dataset to `data/processed/cleaned_wildfire_data.csv`.
            """
        ),
        code(
            """
            from pathlib import Path
            import sys

            import pandas as pd

            ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
            sys.path.insert(0, str(ROOT / "src"))

            from data_utils import (
                build_cleaned_dataset,
                find_raw_dataset,
                read_dataset,
                standardize_columns,
            )
            """
        ),
        markdown("## Locate and preview the raw dataset"),
        code(
            """
            raw_path = find_raw_dataset(ROOT / "data" / "raw")
            raw_path
            """
        ),
        code(
            """
            raw_df = read_dataset(raw_path)
            print(f"Rows: {raw_df.shape[0]:,}")
            print(f"Columns: {raw_df.shape[1]:,}")
            display(raw_df.head())
            """
        ),
        markdown("## Schema, missing values, duplicates, and statistics"),
        code(
            """
            profile_table = pd.DataFrame({
                "column": raw_df.columns,
                "dtype": raw_df.dtypes.astype(str).values,
                "missing_values": raw_df.isna().sum().values,
                "missing_pct": (raw_df.isna().mean().values * 100).round(2),
                "unique_values": [raw_df[col].nunique(dropna=True) for col in raw_df.columns],
            })
            display(profile_table)
            print(f"Duplicate rows: {raw_df.duplicated().sum():,}")
            display(raw_df.describe(include="all").T.head(30))
            """
        ),
        markdown("## Standardize columns and run the cleaning pipeline"),
        code(
            """
            standardized_preview = standardize_columns(raw_df.head())
            standardized_preview.columns.tolist()
            """
        ),
        code(
            """
            clean_df, cleaning_profile, clean_path = build_cleaned_dataset(
                raw_path=raw_path,
                output_path=ROOT / "data" / "processed" / "cleaned_wildfire_data.csv",
            )
            cleaning_profile, clean_path
            """
        ),
        markdown("## Validate cleaned data"),
        code(
            """
            print(f"Clean rows: {len(clean_df):,}")
            print(f"Date range: {clean_df['acq_datetime'].min()} to {clean_df['acq_datetime'].max()}")
            print(f"Latitude range: {clean_df['latitude'].min():.3f} to {clean_df['latitude'].max():.3f}")
            print(f"Longitude range: {clean_df['longitude'].min():.3f} to {clean_df['longitude'].max():.3f}")
            display(clean_df.head())
            """
        ),
        code(
            """
            validation_summary = {
                "invalid_latitude": (~clean_df["latitude"].between(-90, 90)).sum(),
                "invalid_longitude": (~clean_df["longitude"].between(-180, 180)).sum(),
                "missing_datetime": clean_df["acq_datetime"].isna().sum(),
                "duplicate_rows": clean_df.duplicated().sum(),
            }
            validation_summary
            """
        ),
        markdown(
            """
            ## Cleaning notes

            - FIRMS acquisition time is parsed as HHMM and combined with acquisition date into UTC timestamps.
            - Coordinates outside valid latitude and longitude ranges are removed.
            - Duplicate records are dropped after validation.
            - Categorical confidence values such as low, nominal, and high are normalized into a 0-100 score.
            - `brightness_primary` uses the best available brightness field across MODIS and VIIRS variants.
            """
        ),
    ]


def build_eda() -> list:
    return [
        markdown(
            """
            # 02 - Exploratory Data Analysis

            This notebook explores temporal trends, sensor coverage, confidence distribution, thermal intensity,
            day/night behavior, top activity bands, and simple hotspot spike detection.
            """
        ),
        code(
            """
            from pathlib import Path
            import sys

            import pandas as pd
            import plotly.express as px

            ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
            sys.path.insert(0, str(ROOT / "src"))

            from data_utils import load_cleaned_data
            """
        ),
        code(
            """
            df = load_cleaned_data(ROOT / "data" / "processed" / "cleaned_wildfire_data.csv")
            print(df.shape)
            display(df.head())
            """
        ),
        markdown("## Fire detections over time"),
        code(
            """
            daily = (
                df.assign(date=df["acq_datetime"].dt.date)
                .groupby("date", as_index=False)
                .size()
                .rename(columns={"size": "fire_detections"})
            )
            fig = px.line(
                daily,
                x="date",
                y="fire_detections",
                markers=True,
                title="Daily wildfire detections",
                labels={"date": "Date", "fire_detections": "Fire detections"},
            )
            fig.show()

            peak = daily.sort_values("fire_detections", ascending=False).iloc[0]
            print(f"Peak day: {peak['date']} with {int(peak['fire_detections']):,} detections.")
            """
        ),
        markdown("## Hourly detection pattern"),
        code(
            """
            hourly = (
                df.assign(hour=df["acq_datetime"].dt.hour)
                .groupby("hour", as_index=False)
                .size()
                .rename(columns={"size": "fire_detections"})
            )
            fig = px.bar(
                hourly,
                x="hour",
                y="fire_detections",
                title="Detections by acquisition hour",
                labels={"hour": "UTC hour", "fire_detections": "Fire detections"},
            )
            fig.show()
            """
        ),
        markdown("## Confidence, FRP, and brightness distributions"),
        code(
            """
            confidence_counts = df["confidence_label"].value_counts().reset_index()
            confidence_counts.columns = ["confidence_label", "detections"]
            fig = px.bar(
                confidence_counts,
                x="confidence_label",
                y="detections",
                title="Confidence distribution",
                labels={"confidence_label": "Confidence", "detections": "Detections"},
            )
            fig.show()
            display(confidence_counts)
            """
        ),
        code(
            """
            fig = px.histogram(
                df,
                x="frp",
                nbins=80,
                title="Fire Radiative Power distribution",
                labels={"frp": "FRP"},
            )
            fig.show()

            fig = px.histogram(
                df,
                x="brightness_primary",
                nbins=80,
                title="Primary brightness distribution",
                labels={"brightness_primary": "Brightness"},
            )
            fig.show()
            """
        ),
        markdown("## Sensor, satellite, and day/night comparison"),
        code(
            """
            for column in ["instrument", "satellite", "daynight", "lat_band", "season"]:
                if column in df.columns:
                    counts = df[column].value_counts().head(15).reset_index()
                    counts.columns = [column, "detections"]
                    fig = px.bar(
                        counts,
                        x=column,
                        y="detections",
                        title=f"Top {column} values by detections",
                        labels={column: column.replace("_", " ").title(), "detections": "Detections"},
                    )
                    fig.show()
                    display(counts)
            """
        ),
        markdown("## Spike detection"),
        code(
            """
            daily["rolling_mean"] = daily["fire_detections"].rolling(window=3, min_periods=1).mean()
            daily["rolling_std"] = daily["fire_detections"].rolling(window=3, min_periods=1).std().fillna(0)
            denominator = daily["rolling_std"].where(daily["rolling_std"] != 0)
            daily["z_score"] = ((daily["fire_detections"] - daily["rolling_mean"]) / denominator).fillna(0)
            daily["is_spike"] = daily["z_score"] >= 1.5
            display(daily)

            fig = px.scatter(
                daily,
                x="date",
                y="fire_detections",
                color="is_spike",
                size=daily["z_score"].abs() + 1,
                title="Daily hotspot spike detection",
                labels={"fire_detections": "Fire detections", "date": "Date", "is_spike": "Spike"},
            )
            fig.show()
            """
        ),
        markdown(
            """
            ## EDA takeaways

            - Use the daily trend to identify peak monitoring windows.
            - Compare VIIRS and MODIS coverage before interpreting raw counts as true fire incidence.
            - FRP and brightness are right-skewed, so high-intensity events should be reviewed separately.
            - Day/night split helps distinguish detection timing and sensor coverage patterns.
            """
        ),
    ]


def build_geospatial() -> list:
    return [
        markdown(
            """
            # 03 - Geospatial Analysis

            This notebook maps wildfire detections, builds latitude-longitude grid cells, measures hotspot
            density, and ranks areas with the strongest repeated activity.
            """
        ),
        code(
            """
            from pathlib import Path
            import sys

            import pandas as pd
            import plotly.express as px

            ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
            sys.path.insert(0, str(ROOT / "src"))

            from data_utils import load_cleaned_data
            from geo_utils import aggregate_grid_metrics, sample_for_map
            """
        ),
        code(
            """
            df = load_cleaned_data(ROOT / "data" / "processed" / "cleaned_wildfire_data.csv")
            grid_metrics = aggregate_grid_metrics(df, grid_size=1.0)
            grid_metrics.to_csv(ROOT / "data" / "processed" / "grid_metrics.csv", index=False)
            print(f"Grid cells: {len(grid_metrics):,}")
            display(grid_metrics.head(10))
            """
        ),
        markdown("## Global hotspot scatter map"),
        code(
            """
            map_sample = sample_for_map(df, max_points=12000)
            fig = px.scatter_geo(
                map_sample,
                lat="latitude",
                lon="longitude",
                color="daynight" if "daynight" in map_sample.columns else None,
                size="frp" if "frp" in map_sample.columns else None,
                size_max=9,
                opacity=0.55,
                projection="natural earth",
                title="Sampled global wildfire detections",
            )
            fig.update_layout(geo=dict(showland=True, landcolor="#f8fafc", showcountries=True))
            fig.show()
            """
        ),
        markdown("## Grid density heatmap"),
        code(
            """
            fig = px.density_heatmap(
                df,
                x="longitude",
                y="latitude",
                nbinsx=120,
                nbinsy=60,
                title="Hotspot density by latitude and longitude",
                labels={"longitude": "Longitude", "latitude": "Latitude"},
            )
            fig.show()
            """
        ),
        markdown("## Ranked hotspot density clusters"),
        code(
            """
            top_grids = grid_metrics.head(20)
            fig = px.scatter_geo(
                top_grids,
                lat="center_lat",
                lon="center_lon",
                size="hotspot_count",
                color="avg_frp" if "avg_frp" in top_grids.columns else "hotspot_count",
                hover_name="grid_label",
                hover_data=["hotspot_count", "avg_brightness", "avg_confidence"],
                projection="natural earth",
                title="Top 20 hotspot grid clusters",
            )
            fig.update_layout(geo=dict(showland=True, landcolor="#f8fafc", showcountries=True))
            fig.show()
            display(top_grids)
            """
        ),
        markdown(
            """
            ## Geospatial takeaways

            - Grid aggregation converts point detections into comparable monitoring areas.
            - Hotspot density and intensity can diverge, so high-count grids and high-FRP grids should both be reviewed.
            - The grid table becomes the base layer for the wildfire risk scoring model.
            """
        ),
    ]


def build_risk_scoring() -> list:
    return [
        markdown(
            """
            # 04 - Wildfire Risk Scoring

            This notebook calculates a 0-100 wildfire risk score for each 1-degree latitude-longitude grid cell.
            The score combines hotspot density, average FRP, brightness, confidence, and recency. Missing
            metrics are skipped automatically.
            """
        ),
        code(
            """
            from pathlib import Path
            import sys

            import pandas as pd
            import plotly.express as px

            ROOT = Path.cwd().parent if Path.cwd().name == "notebooks" else Path.cwd()
            sys.path.insert(0, str(ROOT / "src"))

            from data_utils import load_cleaned_data
            from risk_model import DEFAULT_WEIGHTS, build_and_save_risk_scores, compute_risk_scores
            """
        ),
        markdown("## Score formula"),
        code(
            """
            DEFAULT_WEIGHTS
            """
        ),
        markdown(
            """
            Risk categories:

            - 0-25: Low
            - 26-50: Medium
            - 51-75: High
            - 76-100: Critical
            """
        ),
        code(
            """
            df = load_cleaned_data(ROOT / "data" / "processed" / "cleaned_wildfire_data.csv")
            risk_scores, risk_path = build_and_save_risk_scores(
                df,
                ROOT / "data" / "processed" / "wildfire_risk_scores.csv",
                grid_size=1.0,
            )
            risk_path
            """
        ),
        markdown("## Top risk areas"),
        code(
            """
            columns = [
                "grid_label",
                "risk_score",
                "risk_category",
                "hotspot_count",
                "avg_frp",
                "avg_brightness",
                "avg_confidence",
                "latest_detection",
            ]
            display(risk_scores[columns].head(10))
            """
        ),
        code(
            """
            category_counts = (
                risk_scores["risk_category"]
                .value_counts()
                .reindex(["Low", "Medium", "High", "Critical"])
                .dropna()
                .reset_index()
            )
            category_counts.columns = ["risk_category", "area_count"]
            fig = px.bar(
                category_counts,
                x="risk_category",
                y="area_count",
                title="Risk category distribution",
                labels={"risk_category": "Risk category", "area_count": "Grid cells"},
            )
            fig.show()
            display(category_counts)
            """
        ),
        markdown("## Risk map"),
        code(
            """
            top_for_map = risk_scores.sort_values("risk_score", ascending=False).head(600)
            fig = px.scatter_geo(
                top_for_map,
                lat="center_lat",
                lon="center_lon",
                size="hotspot_count",
                color="risk_category",
                hover_name="grid_label",
                hover_data=["risk_score", "hotspot_count", "avg_frp", "avg_brightness", "latest_detection"],
                projection="natural earth",
                title="Top risk grid cells",
                color_discrete_map={
                    "Low": "#2e7d32",
                    "Medium": "#f9a825",
                    "High": "#ef6c00",
                    "Critical": "#c62828",
                },
            )
            fig.update_layout(geo=dict(showland=True, landcolor="#f8fafc", showcountries=True))
            fig.show()
            """
        ),
        markdown(
            """
            ## Model interpretation

            The score is not a prediction of future ignition. It is a monitoring priority index based on observed
            FIRMS detections. High and Critical grids indicate areas where repeated detections, stronger thermal
            signals, and recent activity overlap.
            """
        ),
    ]


def main() -> None:
    notebooks = {
        "01_data_cleaning.ipynb": build_data_cleaning(),
        "02_exploratory_data_analysis.ipynb": build_eda(),
        "03_geospatial_analysis.ipynb": build_geospatial(),
        "04_wildfire_risk_scoring.ipynb": build_risk_scoring(),
    }
    for filename, cells in notebooks.items():
        write_notebook(NOTEBOOK_DIR / filename, cells)
        print(f"Wrote {filename}")


if __name__ == "__main__":
    main()
