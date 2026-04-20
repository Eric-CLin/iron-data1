import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.title("Interactive Iron Biomarker String Plots")

st.markdown(
    """
    <style>
    .modebar-btn[data-title="Fullscreen"] { display: none}
    </style>
    """,
    unsafe_allow_html=True
)

# CSV loading
df = pd.read_csv("Full_Data_with_CRP_NA_Removed.csv")
df.columns = df.columns.str.strip()

st.sidebar.header("Global Filters")

# Sex filter
sex_filter = st.sidebar.selectbox(
    "Sex",
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

# Sorting 
st.sidebar.header("Sorting")

label_to_column = {v: k for k, v in display_labels.items()}

sort_label = st.sidebar.selectbox(
    "Sort cases by",
    list(display_labels.values())
)

sort_biomarker = label_to_column[sort_label]

sort_order = st.sidebar.radio(
    "Order",
    ["Descending", "Ascending"]
)

# Apply global filters
filtered_df = df.copy()

filtered_df = filtered_df[
    (filtered_df["Age.at.screening"] >= age_min) &
    (filtered_df["Age.at.screening"] <= age_max)
]

if sex_filter != "All":
    if sex_filter == "Male":
        filtered_df = filtered_df[filtered_df["Gender..1M..2F."].astype(int) == 1]
    elif sex_filter == "Female":
        filtered_df = filtered_df[filtered_df["Gender..1M..2F."].astype(int) == 2]

# Biomarker thresholding
st.sidebar.header("Biomarker Filters & Thresholds")

biomarker_ranges = {}
biomarker_thresholds = {}
additional_lines = {}

for b in biomarkers:
    min_val_default = float(df[b].min())
    max_val_default = float(df[b].max())

    # Collapsible sections
    with st.sidebar.expander(display_labels[b], expanded=False):

        min_val = st.number_input(
            f"Min {display_labels[b]}",
            value=min_val_default,
            min_value=min_val_default,
            max_value=max_val_default,
            key=f"{b}_min"
        )

        max_val = st.number_input(
            f"Max {display_labels[b]}",
            value=max_val_default,
            min_value=min_val_default,
            max_value=max_val_default,
            key=f"{b}_max"
        )

        if min_val > max_val:
            st.error(f"Min {display_labels[b]} cannot be greater than Max {display_labels[b]}.")
            st.stop()

        threshold = st.number_input(
            f"{display_labels[b]} threshold (points ≤ threshold = red in all plots)",
            value=0.0,
            key=f"{b}_threshold"
        )
        biomarker_thresholds[b] = threshold

        line_input = st.text_input(
            f"Additional horizontal lines for {display_labels[b]} (comma-separated)",
            value="",
            key=f"{b}_lines"
        )

        if line_input.strip():
            try:
                lines = [float(x.strip()) for x in line_input.split(",")]
            except:
                st.error("Invalid number format for horizontal lines.")
                lines = []
        else:
            lines = []

        additional_lines[b] = lines
        biomarker_ranges[b] = (min_val, max_val)

    # Apply filtering outside expander (unchanged logic)
    filtered_df = filtered_df[
        (filtered_df[b] >= biomarker_ranges[b][0]) &
        (filtered_df[b] <= biomarker_ranges[b][1])
    ]

# Case sorting
ascending = True if sort_order == "Ascending" else False

filtered_df = filtered_df.sort_values(sort_biomarker, ascending=ascending)
filtered_df["case_order"] = range(len(filtered_df))

# Red flag logic
filtered_df["is_red"] = False
for b, thresh in biomarker_thresholds.items():
    if thresh != 0:
        filtered_df["is_red"] |= filtered_df[b] <= thresh


# Plot function
def create_plot(data, biomarker):

    plot_df = data.dropna(subset=[biomarker])

    colors = plot_df["is_red"].map({True: "red", False: "#ADD8E6"})

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

    if biomarker_thresholds[biomarker] != 0:
        fig.add_hline(
            y=biomarker_thresholds[biomarker],
            line_dash="dash",
            line_color="black"
        )

    for y in additional_lines[biomarker]:
        fig.add_hline(y=y, line_dash="dot", line_color="green")

    fig.update_layout(
        height=350,
        xaxis_title="Respondent Sequence Number",
        xaxis=dict(showticklabels=False),
        yaxis_title=display_labels[biomarker],
        autosize=True
    )

    return fig


# Render plots
for b in biomarkers:
    st.plotly_chart(create_plot(filtered_df, b), use_container_width=True)

st.subheader(f"Cohort Size: {len(filtered_df):,}")
st.dataframe(filtered_df)
