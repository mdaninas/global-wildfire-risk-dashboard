# Global Wildfire Risk Intelligence Dashboard

Project ini menganalisis data deteksi titik panas global dari NASA FIRMS dan mengubahnya menjadi dashboard risiko kebakaran berbasis grid. Fokusnya bukan hanya menampilkan titik api, tetapi merangkum area yang paling aktif, tren harian, intensitas termal, dan prioritas pemantauan.

Saya membangun project ini sebagai studi kasus data analytics/geospatial analytics: mulai dari data cleaning, eksplorasi, agregasi spasial, risk scoring, sampai dashboard Streamlit yang bisa dijalankan ulang.

## Why This Project

Dataset hotspot satelit biasanya besar dan mudah menjadi peta titik yang terlalu ramai. Agar lebih berguna untuk analisis, data perlu diringkas menjadi:

- area dengan aktivitas kebakaran tertinggi,
- perubahan jumlah deteksi dari waktu ke waktu,
- perbandingan sensor/satelit,
- indikator intensitas seperti FRP dan brightness,
- skor risiko yang konsisten antar-area.

Output akhirnya adalah dashboard yang membantu membaca prioritas area tanpa harus membuka ratusan ribu baris data mentah.

## Dataset

Full dataset yang digunakan: [NASA FIRMS Multi-Sensor Global Wildfire Detections](https://www.kaggle.com/datasets/sarcasmos/nasa-firms-multi-sensor-global-wildfire-detections) dari Kaggle.

Profil data lokal yang dianalisis:

- Raw records: 565,708
- Clean records: 565,690
- Removed duplicates: 18
- Date range: 2026-04-21 00:01 UTC to 2026-04-25 20:28 UTC
- Instruments: VIIRS 535,025 detections, MODIS 30,665 detections
- Day/night split: 413,582 day detections and 152,108 night detections

Catatan reproducibility:

- Full CSV tidak disimpan di repo karena ukurannya besar.
- Repo menyertakan `data/sample/wildfire_sample.csv` agar dashboard tetap bisa dicoba setelah clone.
- Untuk hasil penuh, download dataset dari Kaggle, letakkan CSV di `data/raw/nasa_firms_multisensor_2026.csv`, lalu jalankan pipeline ulang.

## Workflow

1. Inspect raw schema dan missing values.
2. Standardize nama kolom FIRMS.
3. Parse tanggal dan jam akuisisi menjadi timestamp.
4. Validasi koordinat latitude/longitude.
5. Normalize confidence, FRP, dan brightness antar-sensor.
6. Agregasi titik panas ke grid latitude-longitude 1 derajat.
7. Hitung wildfire risk score 0-100.
8. Visualisasi hasil lewat notebook dan Streamlit dashboard.

## Risk Scoring

Risk score dihitung per grid 1 derajat latitude-longitude. Komponen model:

| Component | Weight |
|---|---:|
| Hotspot density | 35% |
| Average FRP | 20% |
| Average brightness | 15% |
| Average confidence | 15% |
| Recent activity | 15% |

Kategori risiko:

| Score | Category |
|---:|---|
| 0-25 | Low |
| 26-50 | Medium |
| 51-75 | High |
| 76-100 | Critical |

Jika satu metrik tidak tersedia di dataset, model otomatis memakai metrik lain yang tersedia.

## Key Results

- Peak detections terjadi pada 2026-04-22 dengan 128,907 deteksi.
- VIIRS menyumbang mayoritas data, yaitu 535,025 deteksi.
- Latitude band 0-30N memiliki volume deteksi terbesar: 350,120 records.
- Daytime detections lebih banyak dibanding nighttime detections pada window data ini.
- Grid risiko tertinggi: `Lat 10.0 to 11.0, Lon -14.0 to -13.0`.
- Risk score tertinggi: 80.84, kategori Critical.
- Total area prioritas: 6 Critical grids dan 2,269 High-risk grids.

## Dashboard

Dashboard Streamlit berisi:

- KPI ringkas untuk total titik panas, area prioritas, tanggal puncak, dan rata-rata FRP.
- Peta risiko global berbasis grid agregat agar lebih ringan dari plotting semua titik mentah.
- Trend harian deteksi titik panas.
- Distribusi kategori risiko.
- Ranking area prioritas.
- Filter tanggal, kategori risiko, FRP, satelit, instrument, confidence, dan day/night.
- Export risk score hasil filter.

Preview dashboard:

![Dashboard preview](assets/dashboard_preview.png)

## Project Structure

```text
wildfire-risk-intelligence/
|-- app/
|   `-- streamlit_app.py
|-- assets/
|   `-- dashboard_preview.png
|-- data/
|   |-- raw/
|   |   `-- nasa_firms_multisensor_2026.csv        # optional full dataset
|   |-- sample/
|   |   `-- wildfire_sample.csv                    # small demo dataset
|   `-- processed/
|       |-- cleaned_wildfire_data.csv              # generated
|       `-- wildfire_risk_scores.csv               # generated
|-- notebooks/
|   |-- 01_data_cleaning.ipynb
|   |-- 02_exploratory_data_analysis.ipynb
|   |-- 03_geospatial_analysis.ipynb
|   `-- 04_wildfire_risk_scoring.ipynb
|-- reports/
|   |-- data_profile.json
|   `-- executive_summary.md
|-- src/
|   |-- data_utils.py
|   |-- geo_utils.py
|   |-- risk_model.py
|   |-- build_outputs.py
|   `-- create_notebooks.py
|-- requirements.txt
`-- README.md
```

## How to Run

Install dependencies:

```bash
pip install -r requirements.txt
```

Build cleaned data and risk scores:

```bash
python src/build_outputs.py
```

Run dashboard:

```bash
streamlit run app/streamlit_app.py
```

If `data/raw/` is empty, the pipeline uses the sample dataset in `data/sample/`. For the full analysis, download the Kaggle CSV and place it in `data/raw/`.

## Notebooks

- `01_data_cleaning.ipynb`: schema inspection, validation, cleaning.
- `02_exploratory_data_analysis.ipynb`: trend, confidence, FRP, satellite, day/night analysis.
- `03_geospatial_analysis.ipynb`: grid aggregation and hotspot density.
- `04_wildfire_risk_scoring.ipynb`: scoring method, ranking, and risk map.

## Limitations

- Risk score is an observed activity index, not a fire prediction model.
- The current full dataset covers 2026-04-21 to 2026-04-25 UTC.
- Grid-based ranking does not replace administrative boundary analysis.
- Satellite detections can be affected by overpass timing, cloud cover, sensor type, and detection algorithm.
- Weather, land cover, fuel moisture, and population exposure are not included yet.

## Next Improvements

- Add country/province boundaries for more readable regional summaries.
- Add a longer historical baseline for anomaly detection.
- Add weather and vegetation variables for predictive modeling.
- Add automated report export from the dashboard.

## Author

Personal data analytics and geospatial analytics portfolio project.
