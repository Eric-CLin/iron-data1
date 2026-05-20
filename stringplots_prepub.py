import streamlit as st
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(layout="wide")

st.title("Interactive Iron Biomarker String Plots, NHANES 2017-2020 Pre-Pandemic Data")

st.markdown(
    """
    <style>
    .modebar-btn[data-title="Fullscreen"] { display: none}
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <style>
    .modebar-btn[data-title="Fullscreen"] { display: none}
    </style>
    """,
    unsafe_allow_html=True
)

# CSV loading

df = pd.read_csv("Iron_Data_Na_Removed.csv")
df.columns = df.columns.str.strip()

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

# Convert numeric
for b in biomarkers:
    df[b] = pd.to_numeric(df[b], errors="coerce")

df["Age.at.screening"] = pd.to_numeric(df["Age.at.screening"], errors="coerce")

df = df.dropna(subset=biomarkers + ["Age.at.screening", "SEQN.Respondent.Sequence.Number"])

# Default 0 value for thresholds

if "thresholds" not in st.session_state:
    st.session_state.thresholds = {b: 0.0 for b in biomarkers}

if "additional_lines" not in st.session_state:
    st.session_state.additional_lines = {b: [] for b in biomarkers}

# One active threshold allowed at a time

def set_single_threshold(active_biomarker):
    for b in biomarkers:
        if b != active_biomarker:
            st.session_state[f"thresh_{b}"] = 0.0
            st.session_state.thresholds[b] = 0.0

    st.session_state.thresholds[active_biomarker] = st.session_state[f"thresh_{active_biomarker}"]

    # UX feedback
    st.toast(f"Threshold set for {display_labels[active_biomarker]} — others reset")

# Sidebar filters

st.sidebar.header("Global Filters")

sex_filter = st.sidebar.selectbox("Sex", ["All", "Male", "Female"])

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

# Data sorting 

st.sidebar.header("Sorting")

label_to_column = {v: k for k, v in display_labels.items()}

sort_label = st.sidebar.selectbox("Sort cases by", list(display_labels.values()))
sort_biomarker = label_to_column[sort_label]

sort_order = st.sidebar.radio("Order", ["Descending", "Ascending"])
ascending = sort_order == "Ascending"

# Global filters

filtered_df = df.copy()

filtered_df = filtered_df[
    (filtered_df["Age.at.screening"] >= age_min) &
    (filtered_df["Age.at.screening"] <= age_max)
]

if sex_filter != "All":
    filtered_df["Gender..1M..2F."] = pd.to_numeric(
        filtered_df["Gender..1M..2F."],
        errors="coerce"
    )

    if sex_filter == "Male":
        filtered_df = filtered_df[filtered_df["Gender..1M..2F."] == 1]
    elif sex_filter == "Female":
        filtered_df = filtered_df[filtered_df["Gender..1M..2F."] == 2]

st.subheader(f"Cases After Age and Sex Filters: {len(filtered_df):,}")

# Biomarker filtering

st.sidebar.header("Biomarker Filters & Thresholds")

for b in biomarkers:
    min_val_default = float(df[b].min())
    max_val_default = float(df[b].max())

    with st.sidebar.expander(display_labels[b], expanded=False):

        st.number_input(
            f"Min {display_labels[b]}",
            value=min_val_default,
            min_value=min_val_default,
            max_value=max_val_default,
            key=f"{b}_min"
        )

        st.number_input(
            f"Max {display_labels[b]}",
            value=max_val_default,
            min_value=min_val_default,
            max_value=max_val_default,
            key=f"{b}_max"
        )

        # Threshold (with reset)
        st.number_input(
            f"{display_labels[b]} threshold (≤ = red)",
            value=st.session_state.thresholds[b],
            key=f"thresh_{b}",
            on_change=set_single_threshold,
            args=(b,)
        )

        # Additional lines
        line_input = st.text_input(
            f"Additional horizontal lines (comma-separated)",
            value="",
            key=f"lines_{b}"
        )

        if line_input.strip():
            try:
                st.session_state.additional_lines[b] = [
                    float(x.strip()) for x in line_input.split(",")
                ]
            except:
                st.error("Invalid number format for horizontal lines.")
                st.session_state.additional_lines[b] = []
        else:
            st.session_state.additional_lines[b] = []

# Biomarker filtering

mask = pd.Series(True, index=df.index)

for b in biomarkers:
    min_val = st.session_state.get(f"{b}_min", float(df[b].min()))
    max_val = st.session_state.get(f"{b}_max", float(df[b].max()))
    mask &= df[b].between(min_val, max_val)

filtered_df = filtered_df[mask.loc[filtered_df.index]]

st.subheader(f"Cases After All Biomarker Filters: {len(filtered_df):,}")

# Sorting

filtered_df = filtered_df.sort_values(sort_biomarker, ascending=ascending)
filtered_df["case_order"] = range(len(filtered_df))

# Red case logic

filtered_df["is_red"] = False

for b, thresh in st.session_state.thresholds.items():
    if thresh != 0:
        filtered_df["is_red"] |= filtered_df[b] <= thresh

# Plot logic

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
                f"{display_labels[biomarker]}: %{{y:.2f}}<extra></extra>"
            ),
            customdata=plot_df[[
                "SEQN.Respondent.Sequence.Number",
                "Age.at.screening",
                "Gender..1M..2F."
            ]].values
        )
    )

    thresh = st.session_state.thresholds[biomarker]

    if thresh != 0:
        fig.add_hline(y=thresh, line_dash="dash", line_color="black")

    for y in st.session_state.additional_lines[biomarker]:
        fig.add_hline(y=y, line_dash="dot", line_color="green")

    fig.update_layout(
        height=350,
        xaxis_title="Respondent Sequence Number",
        xaxis=dict(showticklabels=False),
        yaxis_title=display_labels[biomarker],
        autosize=True
    )

    return fig

# Plot rendering

for b in biomarkers:
    st.plotly_chart(create_plot(filtered_df, b), use_container_width=True)

st.dataframe(filtered_df)

# Case search bar 
st.subheader("Case Lookup")
case_search = st.text_input("Enter Case ID Number (Respondent Sequence Number)")

# Selected case logic 

selected_case_df = pd.DataFrame()
selected_case = None

if case_search:
    try:
        selected_case = float(case_search)

        selected_case_df = filtered_df[
            filtered_df["SEQN.Respondent.Sequence.Number"] == selected_case
        ]

    except:
        st.error("Invalid Case ID format.")

# Selected case output table 

st.subheader("Selected Case")

if case_search and not selected_case_df.empty:

    st.dataframe(selected_case_df)

    st.markdown("### Biomarker Values for Selected Case")

    biomarker_display = selected_case_df[biomarkers].T
    biomarker_display.columns = ["Value"]
    biomarker_display.index = biomarker_display.index.map(
        display_labels
    )

    st.dataframe(biomarker_display)

elif case_search:
    st.warning("Case ID not found in filtered dataset.")

else:
    st.info("Enter a Case ID to view details.")
