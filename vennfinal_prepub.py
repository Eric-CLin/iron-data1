import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(layout="wide")
st.title("Patient Venn Explorer, NHANES 2017-2020 Pre-Pandemic Data")

st.markdown(
    """
    <style>
    .modebar-btn[data-title="Fullscreen"] { display: none}
    </style>
    """,
    unsafe_allow_html=True
)

# Data file loading
data_path = "Full_Data_with_CRP_NA_Removed.csv"
df = pd.read_csv(data_path)
df.columns = df.columns.str.strip()

AGE_COLUMN = "Age.at.screening"
GENDER_COLUMN = "Gender..1M..2F."
IRON_COLUMN = "LBDIRNSI.Iron.Frozen.Serum..umol.L."
FERRITIN_COLUMN = "LBDFERSI.Ferritin..ug.L."
TSAT_COLUMN = "LBDPCT.Transferrin.Saturation.."
HGB_COLUMN = "LBXHGB.Hemoglobin..g.dL."

REQUIRED_COLUMNS = [AGE_COLUMN, GENDER_COLUMN, IRON_COLUMN, FERRITIN_COLUMN, TSAT_COLUMN, HGB_COLUMN]
missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
if missing:
    st.error(f"Missing required columns: {missing}")
    st.stop()

for col in REQUIRED_COLUMNS:
    if col != GENDER_COLUMN:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(r"[^\d\.\-]", "", regex=True), errors="coerce")
df = df.dropna(subset=REQUIRED_COLUMNS).copy()

# Sidebar filters
st.sidebar.header("Filters")

def dual_number_input(label, column, integer=False):
    min_val = float(np.floor(df[column].min()))
    max_val = float(np.ceil(df[column].max()))

    col1, col2 = st.sidebar.columns(2)

    if integer:
        min_val = int(min_val)
        max_val = int(max_val)

        min_input = col1.number_input(
            f"{label} Min",
            min_value=min_val,
            max_value=max_val,
            value=min_val,
            step=1,
            format="%d",
            key=f"{column}_min"
        )
        max_input = col2.number_input(
            f"{label} Max",
            min_value=min_val,
            max_value=max_val,
            value=max_val,
            step=1,
            format="%d",
            key=f"{column}_max"
        )
    else:
        min_input = col1.number_input(
            f"{label} Min",
            min_value=min_val,
            max_value=max_val,
            value=min_val,
            key=f"{column}_min"
        )
        max_input = col2.number_input(
            f"{label} Max",
            min_value=min_val,
            max_value=max_val,
            value=max_val,
            key=f"{column}_max"
        )

    if min_input > max_input:
        max_input = min_input

    return min_input, max_input


# Age (INTEGER ONLY)
age_min, age_max = dual_number_input("Age Range", AGE_COLUMN, integer=True)

# Gender mapping (1/2 → Male/Female)
gender_map = {1: "Male", 2: "Female"}
reverse_gender_map = {"Male": 1, "Female": 2}

available_genders = sorted(df[GENDER_COLUMN].dropna().unique())
gender_labels = [gender_map[g] for g in available_genders if g in gender_map]

selected_labels = st.sidebar.multiselect(
    "Sex",
    gender_labels,
    default=gender_labels
)

gender_choice = [reverse_gender_map[label] for label in selected_labels]

# Biomarker filters (keep decimals)
hgb_min, hgb_max = dual_number_input("Hemoglobin Range (g/dL)", HGB_COLUMN)
iron_min, iron_max = dual_number_input("Iron Range (μmol/L)", IRON_COLUMN)
ferritin_min, ferritin_max = dual_number_input("Ferritin Range (μg/L)", FERRITIN_COLUMN)
tsat_min, tsat_max = dual_number_input("TSAT Range (%)", TSAT_COLUMN)

df = df[
    (df[AGE_COLUMN] >= age_min) & (df[AGE_COLUMN] <= age_max) &
    (df[GENDER_COLUMN].isin(gender_choice)) &
    (df[HGB_COLUMN] >= hgb_min) & (df[HGB_COLUMN] <= hgb_max)
].copy()

if df.empty:
    st.warning("No data available for the selected filters.")
    st.stop()

# Venn categories
df["A"] = df[IRON_COLUMN].between(iron_min, iron_max)
df["B"] = df[FERRITIN_COLUMN].between(ferritin_min, ferritin_max)
df["C"] = df[TSAT_COLUMN].between(tsat_min, tsat_max)

df = df[df[["A", "B", "C"]].any(axis=1)].copy()

def compute_region(row):
    if row["A"] and row["B"] and row["C"]:
        return "ABC"
    elif row["A"] and row["B"]:
        return "AB"
    elif row["A"] and row["C"]:
        return "AC"
    elif row["B"] and row["C"]:
        return "BC"
    elif row["A"]:
        return "A"
    elif row["B"]:
        return "B"
    elif row["C"]:
        return "C"
    else:
        return "None"

df["Region"] = df.apply(compute_region, axis=1)

conditions = ["A", "B", "C", "AB", "AC", "BC", "ABC"]
region_counts = df["Region"].value_counts().to_dict()
for key in conditions:
    region_counts.setdefault(key, 0)

st.subheader(f"Cases After Filters: {len(df):,}")

# Venn plot
fig = go.Figure()

center_x, center_y = 0.5, 0.5
fig_width = 0.9
fig_height = 0.9
triangle_offset = 0.25 * fig_width
radius = 0.25

iron_x, iron_y = center_x - triangle_offset / 2, center_y - triangle_offset * np.sin(np.pi / 3) / 2
ferritin_x, ferritin_y = center_x + triangle_offset / 2, center_y - triangle_offset * np.sin(np.pi / 3) / 2
tsat_x, tsat_y = center_x, center_y + triangle_offset * np.sin(np.pi / 3) / 2

theta = np.linspace(0, 2 * np.pi, 500)

centers = {
    "Iron": (iron_x, iron_y, "rgba(0,100,255,0.35)"),
    "Ferritin": (ferritin_x, ferritin_y, "rgba(0,200,120,0.35)"),
    "TSAT": (tsat_x, tsat_y, "rgba(255,80,80,0.35)")
}

for label, (cx, cy, color) in centers.items():
    fig.add_trace(go.Scatter(
        x=cx + radius * np.cos(theta),
        y=cy + radius * np.sin(theta),
        fill="toself",
        mode="lines",
        fillcolor=color,
        line=dict(width=2),
        hoverinfo="skip",
        showlegend=False
    ))

# Region labels
region_positions = {
    "A": (iron_x - 0.15 * fig_width, iron_y - 0.05 * fig_height),
    "B": (ferritin_x + 0.15 * fig_width, ferritin_y - 0.05 * fig_height),
    "C": (tsat_x, tsat_y + 0.15 * fig_height),
    "AB": (center_x, iron_y - 0.1 * fig_height),
    "AC": ((iron_x + tsat_x) / 2 - 0.07 * fig_width, (iron_y + tsat_y) / 2 + 0.07 * fig_height),
    "BC": ((ferritin_x + tsat_x) / 2 + 0.07 * fig_width, (ferritin_y + tsat_y) / 2 + 0.07 * fig_height),
    "ABC": (center_x, center_y - 0.03 * fig_height)
}

total_n = len(df)

for region, pos in region_positions.items():
    count = region_counts[region]
    percent = (count / total_n * 100) if total_n else 0

    fig.add_annotation(
        x=pos[0],
        y=pos[1],
        text=f"{count}<br>({percent:.1f}%)",
        showarrow=False,
        font=dict(size=22, color="black"),
        xanchor="center",
        yanchor="middle"
    )

# Exterior labels
label_distance = 0.35 * fig_width
exterior_labels = [
    (iron_x, iron_y, f"Iron\n({iron_min}-{iron_max} μmol/L)"),
    (ferritin_x, ferritin_y, f"Ferritin\n({ferritin_min}-{ferritin_max} μg/L)"),
    (tsat_x, tsat_y - 0.02 * fig_height, f"TSAT\n({tsat_min}-{tsat_max}%)")
]

for cx, cy, text in exterior_labels:
    vec = np.array([cx - center_x, cy - center_y])
    vec = vec / np.linalg.norm(vec)
    fig.add_annotation(
        x=cx + vec[0] * label_distance,
        y=cy + vec[1] * label_distance,
        text=text,
        showarrow=False,
        font=dict(size=16, color="black"),
        xanchor="center"
    )

# Layout
fig.update_layout(
    width=900,
    height=900,
    plot_bgcolor="white",
    margin=dict(l=0, r=0, t=0, b=0),
    xaxis=dict(visible=False, scaleanchor="y", constrain='domain'),
    yaxis=dict(visible=False)
)

col1, col2, col3 = st.columns([1, 6, 1])
with col2:
    st.plotly_chart(fig, use_container_width=False)

st.subheader(f"Cohort Size: {len(df):,}")
selected_region = st.radio("Select Region", ["All"] + conditions, horizontal=True)
st.dataframe(df if selected_region == "All" else df[df["Region"] == selected_region])
