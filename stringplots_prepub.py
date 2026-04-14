import streamlit as st
import pandas as pd
import plotly.graph_objects as go

def wide_space_default():
st.set_page_config(layout=“wide”)

wide_space_default()

st.title("Interactive Iron Biomarker String Plots")

# CSV loading
uploaded_file = st.file_uploader("Upload Patient CSV")

if uploaded_file is None:
    st.stop()

# -----------------------------
# LOAD DATA
# -----------------------------
df = pd.read_csv(uploaded_file)
df.columns = df.columns.str.strip()

st.sidebar.header("Global Filters")

# Sex filter
sex_filter = st.sidebar.selectbox(
    "Gender",
    ["All", "Male", "Female"]
)

min_age_default = int(df["Age.at.screening"].min())
max_age_default = int(df["Age.at.screening"].max())

st.sidebar.subheader("Age Range")
age_min = st.sidebar.number_input(
    "Min Age",
    value=min_age_default,
    min_value=min_age_default,
    max_value=max_age_default
)
age_max = st.sidebar.number_input(
    "Max Age",
    value=max_age_default,
    min_value=min_age_default,
    max_value=max_age_default
)

if age_min > age_max:
    st.sidebar.error("Min Age cannot be greater than Max Age.")
    st.stop()

biomarkers = [
    "LBDIRNSI.Iron.Frozen.Serum..umol.L.",
    "LBDFERSI.Ferritin..ug.L.",
    "LBXHGB.Hemoglobin..g.dL.",
    "LBDPCT.Transferrin.Saturation.."
]

display_labels = {
    "LBDIRNSI.Iron.Frozen.Serum..umol.L.": "Iron μmol/L",
    "LBDFERSI.Ferritin..ug.L.": "Ferritin μg/L",
    "LBXHGB.Hemoglobin..g.dL.": "Hemoglobin g/dL",
    "LBDPCT.Transferrin.Saturation..": "TSAT %"
}

# Convert biomarker columns to numeric
for b in biomarkers:
    df[b] = pd.to_numeric(df[b], errors="coerce")

df["Age.at.screening"] = pd.to_numeric(df["Age.at.screening"], errors="coerce")

df = df.dropna(subset=biomarkers + ["Age.at.screening", "SEQN.Respondent.Sequence.Number"])

# Sorting options (UPDATED)
biomarker_display_map = {v: k for k, v in display_labels.items()}

sort_biomarker_display = st.sidebar.selectbox(
    "Sort cases by",
    list(display_labels.values())
)

sort_biomarker = biomarker_display_map[sort_biomarker_display]

sort_order = st.sidebar.radio(
    "Order",
    ["Ascending", "Descending"]
)

# Apply global filters
filtered_df = df.copy()

filtered_df = filtered_df[
    (filtered_df["Age.at.screening"] >= age_min) &
    (filtered_df["Age.at.screening"] <= age_max)
]

if sex_filter != "All":
    gender_map = {"Male": 1, "Female": 2}
    filtered_df = filtered_df[
        filtered_df["Gender..1M..2F."] == gender_map[sex_filter]
    ]

# Biomarker thresholding
st.sidebar.header("Biomarker Filters & Thresholds")

biomarker_ranges = {}
biomarker_thresholds = {}
additional_lines = {}

for b in biomarkers:
    min_val_default = float(df[b].min())
    max_val_default = float(df[b].max())

    st.sidebar.subheader(display_labels[b])

    min_val = st.sidebar.number_input(
        f"Min {display_labels[b]}",
        value=min_val_default,
        min_value=min_val_default,
        max_value=max_val_default,
        key=f"min_{b}"
    )

    max_val = st.sidebar.number_input(
        f"Max {display_labels[b]}",
        value=max_val_default,
        min_value=min_val_default,
        max_value=max_val_default,
        key=f"max_{b}"
    )

    if min_val > max_val:
        st.sidebar.error(f"Min {display_labels[b]} cannot be greater than Max {display_labels[b]}.")
        st.stop()

    threshold = st.sidebar.number_input(
        f"{display_labels[b]} threshold (points ≤ threshold = red in all plots)",
        value=float(min_val_default),
        key=f"thresh_{b}"
    )

    biomarker_thresholds[b] = threshold

    line_input = st.sidebar.text_input(
        f"Additional horizontal lines for {display_labels[b]} (comma-separated)",
        value="",
        key=f"lines_{b}"
    )

    if line_input.strip():
        try:
            lines = [float(x.strip()) for x in line_input.split(",")]
        except:
            st.sidebar.error("Invalid number format for horizontal lines.")
            lines = []
    else:
        lines = []

    additional_lines[b] = lines
    biomarker_ranges[b] = (min_val, max_val)

    filtered_df = filtered_df[
        (filtered_df[b] >= min_val) & (filtered_df[b] <= max_val)
    ]

# Sorting
ascending = True if sort_order == "Ascending" else False
filtered_df = filtered_df.sort_values(sort_biomarker, ascending=ascending)
filtered_df["case_order"] = range(len(filtered_df))

# -----------------------------
# VERTICAL LINE CONTROL
# -----------------------------
if "vline_pos" not in st.session_state:
    st.session_state.vline_pos = 0

st.sidebar.header("Vertical Line Control")

biomarker_display_map = {v: k for k, v in display_labels.items()}

selected_biomarker_display = st.sidebar.selectbox(
    "Biomarker for positioning",
    list(display_labels.values()),
    key="vline_biomarker"
)

selected_biomarker_for_line = biomarker_display_map[selected_biomarker_display]

input_value = st.sidebar.number_input(
    f"Enter {display_labels[selected_biomarker_for_line]} value",
    value=0.0,
    key="vline_value"
)

# Map biomarker value to closest case
if not filtered_df.empty:
    temp_df = filtered_df.copy()
    temp_df["distance"] = (temp_df[selected_biomarker_for_line] - input_value).abs()

    closest_idx = temp_df["distance"].idxmin()
    closest_case_order = int(filtered_df.loc[closest_idx, "case_order"])

    st.session_state.vline_pos = closest_case_order

# Red mask
red_mask = pd.Series(False, index=filtered_df.index)
for b, thresh in biomarker_thresholds.items():
    red_mask = red_mask | (filtered_df[b] <= thresh)

# Plot function
def create_plot(data, biomarker):
    plot_df = data.dropna(subset=[biomarker])

    colors = ["red" if red_mask.loc[idx] else "#ADD8E6" for idx in plot_df.index]

    fig = go.Figure()

    fig.add_trace(
        go.Scatter(
            x=plot_df["case_order"],
            y=plot_df[biomarker],
            mode="markers",
            marker=dict(color=colors),
            hovertemplate=(
                "Case: %{customdata[0]}<br>"
                "Age: %{customdata[1]}<br>"
                "Gender: %{customdata[2]}<br>"
                f"{display_labels[biomarker]}: %{{y}}"
            ),
            customdata=plot_df[[
                "SEQN.Respondent.Sequence.Number",
                "Age.at.screening",
                "Gender..1M..2F."
            ]].values
        )
    )

    fig.add_hline(
        y=biomarker_thresholds[biomarker],
        line_dash="dash",
        line_color="black"
    )

    for y in additional_lines[biomarker]:
        fig.add_hline(y=y, line_dash="dot", line_color="green")

    # Vertical line (green)
    fig.add_vline(
        x=st.session_state.vline_pos,
        line_dash="dash",
        line_color="green"
    )

    fig.update_layout(
        height=350,
        xaxis_title="Respondent Sequence Number",
        yaxis_title=display_labels[biomarker],
        autosize=True
    )

    return fig

# Render plots
for b in biomarkers:
    st.plotly_chart(create_plot(filtered_df, b), use_container_width=True)

st.subheader(f"Cohort Size: {len(filtered_df):,}")
st.dataframe(filtered_df)
