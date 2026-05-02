from __future__ import annotations

import html
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from data_utils import build_cleaned_dataset, find_raw_dataset, load_cleaned_data
from geo_utils import add_grid_columns
from risk_model import build_and_save_risk_scores


PROCESSED_DIR = ROOT_DIR / "data" / "processed"
CLEANED_PATH = PROCESSED_DIR / "cleaned_wildfire_data.csv"
RISK_PATH = PROCESSED_DIR / "wildfire_risk_scores.csv"

RISK_LABELS = {
    "Low": "Rendah",
    "Medium": "Sedang",
    "High": "Tinggi",
    "Critical": "Kritis",
    "Unknown": "Tidak diketahui",
}
RISK_LABEL_ORDER = ["Rendah", "Sedang", "Tinggi", "Kritis"]
RISK_LABEL_COLORS = {
    "Rendah": "#2e7d32",
    "Sedang": "#f4a261",
    "Tinggi": "#e76f51",
    "Kritis": "#b42318",
    "Tidak diketahui": "#64748b",
}
RISK_FILTERS = {
    "Semua kategori": ["Low", "Medium", "High", "Critical", "Unknown"],
    "Tinggi + Kritis": ["High", "Critical"],
    "Hanya Kritis": ["Critical"],
    "Rendah + Sedang": ["Low", "Medium"],
}


st.set_page_config(
    page_title="Pantauan Risiko Kebakaran",
    layout="wide",
    initial_sidebar_state="expanded",
)


st.markdown(
    """
    <style>
    .main .block-container {
        padding-top: 1.2rem;
        padding-bottom: 2rem;
        max-width: 1420px;
    }
    h1, h2, h3 {
        letter-spacing: 0;
    }
    [data-testid="stSidebar"] {
        background: #eef3f8;
    }
    [data-testid="stSidebar"] label {
        color: #243447;
        font-weight: 650;
    }
    .page-header {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        align-items: flex-end;
        border-bottom: 1px solid #d9e2ec;
        padding-bottom: 1.1rem;
        margin-bottom: 1rem;
    }
    .page-title {
        color: #172033;
        font-size: clamp(2rem, 3vw, 3rem);
        font-weight: 820;
        line-height: 1.08;
        margin: 0 0 0.45rem;
    }
    .page-subtitle {
        color: #526173;
        font-size: 1rem;
        line-height: 1.5;
        max-width: 820px;
        margin: 0;
    }
    .data-status {
        border: 1px solid #d9e2ec;
        border-radius: 8px;
        background: #ffffff;
        min-width: 230px;
        padding: 0.75rem 0.9rem;
        box-shadow: 0 1px 4px rgba(15, 23, 42, 0.05);
    }
    .status-label {
        color: #66758a;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        font-weight: 760;
    }
    .status-value {
        color: #172033;
        font-size: 0.94rem;
        font-weight: 700;
        margin-top: 0.2rem;
    }
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.85rem;
        margin: 0.8rem 0 1rem;
    }
    .kpi-card {
        border: 1px solid #d9e2ec;
        border-left: 5px solid var(--accent);
        border-radius: 8px;
        padding: 0.9rem 1rem;
        background: #ffffff;
        box-shadow: 0 1px 5px rgba(15, 23, 42, 0.06);
        min-height: 108px;
    }
    .kpi-label {
        color: #66758a;
        font-size: 0.73rem;
        font-weight: 760;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 0.38rem;
    }
    .kpi-value {
        color: #172033;
        font-size: 1.55rem;
        font-weight: 820;
        line-height: 1.1;
    }
    .kpi-help {
        color: #66758a;
        font-size: 0.8rem;
        margin-top: 0.38rem;
        line-height: 1.35;
    }
    .priority-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 0.85rem;
        margin: 0.4rem 0 1.2rem;
    }
    .priority-card {
        border: 1px solid #d9e2ec;
        border-radius: 8px;
        background: #fbfdff;
        padding: 0.95rem 1rem;
        min-height: 132px;
    }
    .priority-title {
        color: #344256;
        font-size: 0.78rem;
        font-weight: 780;
        letter-spacing: 0.04em;
        text-transform: uppercase;
        margin-bottom: 0.45rem;
    }
    .priority-value {
        color: #172033;
        font-size: 1.05rem;
        font-weight: 780;
        line-height: 1.28;
        margin-bottom: 0.35rem;
    }
    .priority-body {
        color: #5d6b7d;
        font-size: 0.86rem;
        line-height: 1.4;
    }
    .section-note {
        color: #5d6b7d;
        font-size: 0.92rem;
        line-height: 1.45;
        margin-top: -0.35rem;
        margin-bottom: 0.7rem;
    }
    .method-card {
        border: 1px solid #d9e2ec;
        border-radius: 8px;
        background: #ffffff;
        padding: 1rem;
        color: #344256;
        line-height: 1.55;
    }
    .view-note {
        border: 1px solid #d9e2ec;
        border-left: 5px solid #2563eb;
        border-radius: 8px;
        background: #f8fbff;
        color: #344256;
        padding: 0.85rem 1rem;
        line-height: 1.45;
        margin: 0.5rem 0 1rem;
    }
    div[data-testid="stDataFrame"] {
        border: 1px solid #d9e2ec;
        border-radius: 8px;
        overflow: hidden;
    }
    @media (max-width: 1100px) {
        .page-header { display: block; }
        .data-status { margin-top: 0.8rem; }
        .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .priority-grid { grid-template-columns: 1fr; }
    }
    @media (max-width: 720px) {
        .kpi-grid { grid-template-columns: 1fr; }
        .kpi-value { font-size: 1.3rem; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_project_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if CLEANED_PATH.exists():
        detections = load_cleaned_data(CLEANED_PATH)
    else:
        raw_path = find_raw_dataset(ROOT_DIR / "data" / "raw")
        detections, _, _ = build_cleaned_dataset(raw_path, CLEANED_PATH)

    if RISK_PATH.exists():
        risk_scores = pd.read_csv(RISK_PATH)
        if "latest_detection" in risk_scores.columns:
            risk_scores["latest_detection"] = pd.to_datetime(
                risk_scores["latest_detection"], errors="coerce", utc=True
            )
    else:
        risk_scores, _ = build_and_save_risk_scores(detections, RISK_PATH, grid_size=1.0)

    if "grid_id" not in detections.columns:
        detections = add_grid_columns(detections, grid_size=1.0)

    risk_lookup_columns = [
        column for column in ["grid_id", "risk_score", "risk_category"] if column in risk_scores.columns
    ]
    if risk_lookup_columns:
        detections = detections.merge(
            risk_scores[risk_lookup_columns],
            on="grid_id",
            how="left",
            suffixes=("", "_grid"),
        )

    return add_display_columns(detections), add_display_columns(risk_scores)


def add_display_columns(df: pd.DataFrame) -> pd.DataFrame:
    output = df.copy()

    if {"lat_bin", "lon_bin"}.issubset(output.columns):
        lat_start = pd.to_numeric(output["lat_bin"], errors="coerce").round(1)
        lat_end = (lat_start + 1).round(1)
        lon_start = pd.to_numeric(output["lon_bin"], errors="coerce").round(1)
        lon_end = (lon_start + 1).round(1)
        output["area_ringkas"] = (
            "Lat "
            + lat_start.astype("string")
            + " to "
            + lat_end.astype("string")
            + ", Lon "
            + lon_start.astype("string")
            + " to "
            + lon_end.astype("string")
        )
    elif "grid_label" in output.columns:
        output["area_ringkas"] = output["grid_label"].astype("string")

    if "risk_category" in output.columns:
        output["risk_label"] = output["risk_category"].map(RISK_LABELS).fillna("Tidak diketahui")

    return output


def format_number(value: float | int | None, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "N/A"

    text = f"{value:,.{decimals}f}"
    if decimals == 0:
        return text.replace(",", ".")

    whole, decimal = text.split(".")
    return f"{whole.replace(',', '.')},{decimal}"


def escape(value: object) -> str:
    return html.escape(str(value))


def metric_card(label: str, value: str, help_text: str, accent: str) -> str:
    return (
        f"<div class='kpi-card' style='--accent:{escape(accent)}'>"
        f"<div class='kpi-label'>{escape(label)}</div>"
        f"<div class='kpi-value'>{escape(value)}</div>"
        f"<div class='kpi-help'>{escape(help_text)}</div>"
        "</div>"
    )


def priority_card(title: str, value: str, body: str) -> str:
    return (
        "<div class='priority-card'>"
        f"<div class='priority-title'>{escape(title)}</div>"
        f"<div class='priority-value'>{escape(value)}</div>"
        f"<div class='priority-body'>{escape(body)}</div>"
        "</div>"
    )


def filter_by_selectbox(df: pd.DataFrame, column: str, label: str, all_label: str) -> pd.DataFrame:
    values = sorted(df[column].dropna().astype(str).unique())
    if not values:
        return df

    selected = st.selectbox(label, [all_label] + values)
    if selected == all_label:
        return df

    return df.loc[df[column].astype(str) == selected]


def apply_sidebar_filters(df: pd.DataFrame) -> pd.DataFrame:
    filtered = df.copy()

    st.sidebar.title("Filter")

    if "acq_datetime" in filtered.columns and filtered["acq_datetime"].notna().any():
        min_date = filtered["acq_datetime"].min().date()
        max_date = filtered["acq_datetime"].max().date()
        selected_dates = st.sidebar.date_input(
            "Rentang tanggal",
            value=(min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        if isinstance(selected_dates, tuple) and len(selected_dates) == 2:
            start_date, end_date = selected_dates
            date_series = filtered["acq_datetime"].dt.date
            filtered = filtered.loc[(date_series >= start_date) & (date_series <= end_date)]

    if "risk_category" in filtered.columns:
        focus_label = st.sidebar.selectbox(
            "Fokus risiko",
            list(RISK_FILTERS.keys()),
            index=0,
        )
        filtered = filtered.loc[filtered["risk_category"].isin(RISK_FILTERS[focus_label])]

    with st.sidebar.expander("Filter tambahan", expanded=False):
        if "frp" in filtered.columns and filtered["frp"].notna().any():
            max_frp = float(filtered["frp"].quantile(0.99)) if not filtered.empty else 1.0
            selected_frp = st.slider(
                "Minimal intensitas panas (FRP)",
                min_value=0.0,
                max_value=max(1.0, round(max_frp, 2)),
                value=0.0,
                step=0.5,
            )
            filtered = filtered.loc[filtered["frp"].fillna(0) >= selected_frp]

        for column, label, all_label in [
            ("satellite", "Satelit", "Semua satelit"),
            ("instrument", "Instrumen", "Semua instrumen"),
            ("confidence_label", "Confidence", "Semua confidence"),
            ("daynight", "Siang / malam", "Semua waktu"),
        ]:
            if column in filtered.columns:
                filtered = filter_by_selectbox(filtered, column, label, all_label)

    return filtered


def daily_detection_trend(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.assign(tanggal=df["acq_datetime"].dt.date)
        .groupby("tanggal", as_index=False)
        .size()
        .rename(columns={"size": "jumlah_deteksi"})
        .sort_values("tanggal")
    )


def top_area_by_count(df: pd.DataFrame) -> tuple[str, int]:
    if df.empty or "area_ringkas" not in df.columns:
        return "N/A", 0

    counts = df.groupby("area_ringkas").size().sort_values(ascending=False)
    if counts.empty:
        return "N/A", 0

    return str(counts.index[0]), int(counts.iloc[0])


def top_satellite_text(df: pd.DataFrame) -> str:
    if df.empty or "satellite" not in df.columns:
        return "N/A"

    counts = df["satellite"].dropna().astype(str).value_counts()
    if counts.empty:
        return "N/A"

    return f"{counts.index[0]} ({format_number(int(counts.iloc[0]))} deteksi)"


def prepare_risk_table(risk_df: pd.DataFrame, limit: int = 10, detailed: bool = False) -> pd.DataFrame:
    columns = [
        "area_ringkas",
        "risk_score",
        "risk_label",
        "hotspot_count",
        "avg_frp",
    ]
    if detailed:
        columns += ["avg_brightness", "avg_confidence", "latest_detection"]

    table = risk_df.sort_values("risk_score", ascending=False).head(limit)
    table = table[[column for column in columns if column in table.columns]].copy()
    for column, decimals in {
        "risk_score": 1,
        "avg_frp": 2,
        "avg_brightness": 1,
        "avg_confidence": 1,
    }.items():
        if column in table.columns:
            table[column] = table[column].round(decimals)

    rename_map = {
        "area_ringkas": "Area",
        "risk_score": "Skor risiko",
        "risk_label": "Kategori",
        "hotspot_count": "Jumlah deteksi",
        "avg_frp": "Rata-rata FRP",
        "avg_brightness": "Rata-rata brightness",
        "avg_confidence": "Rata-rata confidence",
        "latest_detection": "Deteksi terbaru",
    }
    return table.rename(columns=rename_map)


try:
    detections_df, risk_df = load_project_data()
except Exception as exc:
    st.error(f"Data project belum bisa dibaca: {exc}")
    st.stop()


filtered_df = apply_sidebar_filters(detections_df)
visible_grid_ids = set(filtered_df["grid_id"].dropna()) if "grid_id" in filtered_df.columns else set()
visible_risk_df = (
    risk_df.loc[risk_df["grid_id"].isin(visible_grid_ids)].copy() if visible_grid_ids else risk_df.copy()
)

st.markdown(
    """
    <div class="page-header">
      <div>
        <h1 class="page-title">Pantauan Risiko Kebakaran Global</h1>
        <p class="page-subtitle">
          NASA FIRMS multi-sensor wildfire detections | grid-level risk scoring | global hotspot monitoring
        </p>
      </div>
      <div class="data-status">
        <div class="status-label">Dataset</div>
        <div class="status-value">Cleaned + scored</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if filtered_df.empty:
    st.warning("Tidak ada data untuk kombinasi filter saat ini.")
    st.stop()

total_detections = len(filtered_df)
avg_confidence = filtered_df["confidence_score"].mean() if "confidence_score" in filtered_df.columns else None
intensity_column = "frp" if "frp" in filtered_df.columns and filtered_df["frp"].notna().any() else "brightness_primary"
avg_intensity = filtered_df[intensity_column].mean() if intensity_column in filtered_df.columns else None
priority_area_count = (
    visible_risk_df.loc[visible_risk_df["risk_category"].isin(["High", "Critical"]), "grid_id"].nunique()
    if "risk_category" in visible_risk_df.columns
    else 0
)

daily_trend = daily_detection_trend(filtered_df)
peak_row = daily_trend.sort_values("jumlah_deteksi", ascending=False).iloc[0]
peak_text = f"{peak_row['tanggal']} ({format_number(int(peak_row['jumlah_deteksi']))})"

top_risk = visible_risk_df.sort_values("risk_score", ascending=False).head(1)
top_area_value = "N/A"
top_area_body = "Tidak tersedia."
if not top_risk.empty:
    top_area = top_risk.iloc[0]
    top_area_value = f"{top_area['risk_label']} - skor {format_number(top_area['risk_score'], 1)}"
    top_area_body = (
        f"Area {top_area['area_ringkas']}; {format_number(int(top_area['hotspot_count']))} deteksi."
    )

active_area, active_count = top_area_by_count(filtered_df)
priority_cards = [
    priority_card("Prioritas tertinggi", top_area_value, top_area_body),
    priority_card(
        "Area teraktif",
        f"{format_number(active_count)} deteksi",
        f"Area {active_area}.",
    ),
    priority_card(
        "Satelit utama",
        top_satellite_text(filtered_df),
        "Deteksi terbanyak pada filter aktif.",
    ),
]

active_view = st.radio(
    "Pilih tampilan",
    ["Ringkasan", "Peta Risiko", "Tren & Pola", "Detail Data"],
    horizontal=True,
    label_visibility="collapsed",
)

if active_view == "Ringkasan":
    cards = [
        metric_card("Titik panas", format_number(total_detections), "Deteksi sesuai filter", "#2563eb"),
        metric_card("Area prioritas", format_number(priority_area_count), "Risiko Tinggi / Kritis", "#b42318"),
        metric_card("Tanggal puncak", peak_text, "Deteksi harian tertinggi", "#f4a261"),
        metric_card("FRP rata-rata", format_number(avg_intensity, 2), "Intensitas termal", "#2e7d32"),
    ]
    st.markdown(f"<div class='kpi-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)
    st.markdown(f"<div class='priority-grid'>{''.join(priority_cards)}</div>", unsafe_allow_html=True)

    left, right = st.columns([1.1, 0.9])

    with left:
        st.subheader("Aktivitas per hari")
        fig_trend = px.line(
            daily_trend,
            x="tanggal",
            y="jumlah_deteksi",
            markers=True,
            labels={"tanggal": "Tanggal", "jumlah_deteksi": "Jumlah deteksi"},
        )
        fig_trend.update_traces(line_color="#2563eb", marker_color="#2563eb")
        fig_trend.update_layout(margin=dict(l=0, r=0, t=8, b=0), height=340)
        st.plotly_chart(fig_trend, use_container_width=True, config={"displayModeBar": False})

    with right:
        st.subheader("Sebaran tingkat risiko")
        category_counts = (
            visible_risk_df["risk_label"]
            .value_counts()
            .reindex(RISK_LABEL_ORDER)
            .dropna()
            .reset_index()
        )
        category_counts.columns = ["Kategori", "Jumlah area"]
        fig_category = px.bar(
            category_counts,
            x="Kategori",
            y="Jumlah area",
            color="Kategori",
            color_discrete_map=RISK_LABEL_COLORS,
            category_orders={"Kategori": RISK_LABEL_ORDER},
        )
        fig_category.update_layout(showlegend=False, margin=dict(l=0, r=0, t=8, b=0), height=340)
        st.plotly_chart(fig_category, use_container_width=True, config={"displayModeBar": False})

    st.subheader("10 area yang paling perlu dipantau")
    st.dataframe(prepare_risk_table(visible_risk_df, limit=10), use_container_width=True, hide_index=True)

elif active_view == "Peta Risiko":
    st.subheader("Peta risiko global")
    map_candidates = visible_risk_df.loc[visible_risk_df["risk_category"].isin(["High", "Critical"])].copy()
    if map_candidates.empty:
        map_candidates = visible_risk_df.copy()
    map_candidates = map_candidates.sort_values("risk_score", ascending=False).head(600)

    fig_map = px.scatter_geo(
        map_candidates,
        lat="center_lat",
        lon="center_lon",
        color="risk_label",
        size="hotspot_count",
        color_discrete_map=RISK_LABEL_COLORS,
        category_orders={"risk_label": RISK_LABEL_ORDER},
        hover_name="area_ringkas",
        hover_data={
            "risk_score": ":.1f",
            "hotspot_count": ":,",
            "avg_frp": ":.2f",
            "center_lat": ":.2f",
            "center_lon": ":.2f",
        },
        labels={
            "center_lon": "Longitude",
            "center_lat": "Latitude",
            "risk_label": "Risiko",
            "hotspot_count": "Jumlah deteksi",
        },
        projection="natural earth",
    )
    fig_map.update_layout(
        margin=dict(l=0, r=0, t=8, b=0),
        height=560,
        legend_title_text="Risiko",
        geo=dict(
            showland=True,
            landcolor="#f8fafc",
            showocean=True,
            oceancolor="#eef6ff",
            showcountries=True,
            countrycolor="#cbd5e1",
            coastlinecolor="#94a3b8",
            showframe=False,
            projection_type="natural earth",
        ),
    )
    st.plotly_chart(fig_map, use_container_width=True, config={"displayModeBar": False, "scrollZoom": False})

    st.subheader("Ranking area")
    top_for_bar = visible_risk_df.sort_values("risk_score", ascending=False).head(15).copy()
    fig_risk = px.bar(
        top_for_bar.sort_values("risk_score"),
        x="risk_score",
        y="area_ringkas",
        orientation="h",
        color="risk_label",
        color_discrete_map=RISK_LABEL_COLORS,
        labels={"risk_score": "Skor risiko", "area_ringkas": "Area", "risk_label": "Kategori"},
        hover_data=["hotspot_count", "avg_frp", "avg_brightness", "avg_confidence"],
    )
    fig_risk.update_layout(margin=dict(l=0, r=0, t=8, b=0), height=520, yaxis_title=None)
    st.plotly_chart(fig_risk, use_container_width=True, config={"displayModeBar": False})

elif active_view == "Tren & Pola":
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("Sebaran kekuatan sinyal panas")
        fig_distribution = px.histogram(
            filtered_df,
            x=intensity_column,
            nbins=60,
            labels={intensity_column: "FRP / brightness"},
        )
        fig_distribution.update_traces(marker_color="#e76f51")
        fig_distribution.update_layout(margin=dict(l=0, r=0, t=8, b=0), height=360)
        st.plotly_chart(fig_distribution, use_container_width=True, config={"displayModeBar": False})

    with col_b:
        st.subheader("Kualitas deteksi")
        confidence_counts = filtered_df["confidence_label"].value_counts().reset_index()
        confidence_counts.columns = ["Confidence", "Jumlah deteksi"]
        fig_confidence = px.bar(
            confidence_counts,
            x="Confidence",
            y="Jumlah deteksi",
            labels={"Confidence": "Confidence", "Jumlah deteksi": "Jumlah deteksi"},
        )
        fig_confidence.update_traces(marker_color="#2563eb")
        fig_confidence.update_layout(margin=dict(l=0, r=0, t=8, b=0), height=360)
        st.plotly_chart(fig_confidence, use_container_width=True, config={"displayModeBar": False})

    if "daynight" in filtered_df.columns:
        st.subheader("Siang vs malam")
        daynight_counts = filtered_df["daynight"].value_counts().reset_index()
        daynight_counts.columns = ["Waktu", "Jumlah deteksi"]
        fig_daynight = px.pie(
            daynight_counts,
            names="Waktu",
            values="Jumlah deteksi",
            hole=0.45,
            color="Waktu",
            color_discrete_map={"Day": "#f4a261", "Night": "#1d4ed8", "Unknown": "#64748b"},
        )
        fig_daynight.update_layout(margin=dict(l=0, r=0, t=8, b=0), height=380)
        st.plotly_chart(fig_daynight, use_container_width=True, config={"displayModeBar": False})

elif active_view == "Detail Data":
    st.subheader("Tabel area risiko")
    st.dataframe(
        prepare_risk_table(visible_risk_df, limit=50, detailed=True),
        use_container_width=True,
        hide_index=True,
    )

    st.download_button(
        "Download data sesuai filter",
        data=visible_risk_df.to_csv(index=False).encode("utf-8"),
        file_name="wildfire_risk_scores_filtered.csv",
        mime="text/csv",
    )

    st.subheader("Cara skor risiko dihitung")
    st.markdown(
        """
        <div class="method-card">
        Unit analisis: grid latitude-longitude 1 derajat.<br>
        Rentang skor: 0-100.<br>
        Komponen: jumlah titik panas, FRP, brightness, confidence, dan aktivitas terbaru.
        <br><br>
        Kategori: Rendah = 0-25, Sedang = 26-50, Tinggi = 51-75, Kritis = 76-100.
        </div>
        """,
        unsafe_allow_html=True,
    )
