# Executive Summary

## Overview

This project analyzes NASA FIRMS multi-sensor global wildfire detections and converts hotspot points into a professional wildfire risk intelligence workflow. The goal is to identify where wildfire activity is concentrated, when detection volume spikes, and which grid cells should be prioritized for monitoring.

## Methodology

The pipeline loads the local FIRMS CSV, standardizes columns, parses acquisition date and HHMM time into UTC timestamps, validates coordinates, removes duplicates, normalizes confidence, and creates a cross-sensor brightness proxy. Clean data is saved to `data/processed/cleaned_wildfire_data.csv`.

Geospatial analysis uses 1-degree latitude/longitude grids. Each grid is ranked using hotspot count, average FRP, average brightness, average confidence, and recent activity. The weighted score produces a 0-100 risk value and a risk category: Low, Medium, High, or Critical.

## Key Findings

- The cleaned dataset contains 565,690 valid detections from 2026-04-21 to 2026-04-25 UTC.
- Peak detection volume occurs on 2026-04-22 with 128,907 detections.
- VIIRS contributes most detections with 535,025 records, while MODIS contributes 30,665.
- Daytime detections account for 413,582 records, compared with 152,108 nighttime records.
- The most active latitude band is 0-30N with 350,120 detections.
- The model identifies 6 Critical grid cells, 2,269 High-risk grid cells, 4,508 Medium-risk grid cells, and 36 Low-risk grid cells.

## Highest-Risk Areas

The top risk grid is `10.0 to 11.0 lat, -14.0 to -13.0 lon`, with:

- Risk score: 80.84
- Risk category: Critical
- Hotspot count: 3,208
- Average FRP: 44.68
- Average brightness: 344.80
- Latest detection: 2026-04-25 16:37 UTC

Other Critical grids cluster around nearby coordinates between roughly 8-12 latitude and -14 to -12 longitude, plus a high-intensity grid at 22-23 latitude and 93-94 longitude.

## Recommendations

- Prioritize Critical and High-risk grids for monitoring, especially where high hotspot density overlaps with high FRP and recent activity.
- Treat raw detection counts as sensor-influenced observations, not direct fire area estimates.
- Review the top-ranked grids using local context, administrative boundaries, and field reports before operational decisions.
- Use daily monitoring around peak activity windows, with special attention to sudden detection increases.
- Extend this workflow with weather, vegetation, and historical baselines for stronger risk forecasting.

## Limitations

- The score is an observed activity index, not a future fire prediction model.
- The current dataset covers a short window from 2026-04-21 to 2026-04-25 UTC.
- Grid cells do not align with administrative boundaries or ecological zones.
- Satellite detection counts are affected by sensor coverage, overpass timing, cloud cover, and detection algorithms.
- No external context such as weather, fuel moisture, land cover, population exposure, or response capacity is included.

## Next Steps

- Add country and region boundaries for more interpretable geographic reporting.
- Build a longer historical baseline for anomaly detection.
- Add climate and vegetation features to support predictive modeling.
- Add automated exports for dashboard screenshots and scheduled reports.
