import pandas as pd
import plotly.express as px
import streamlit as st
from cart_data import ANTIGEN_LIST, filter_trials, get_trials

# ==============================================================================
# 1. PAGE CONFIGURATION & DATA INITIALIZATION
# ==============================================================================
st.set_page_config(page_title="CAR-T Clinical Trial Landscape", layout="wide")

# Load clinical trial dataset
df = get_trials()

# Page Header
st.title("🛡️ CAR-T Clinical Trial Landscape")

# ==============================================================================
# 2. SIDEBAR FILTERS (SEQUENTIAL FILTERING PIPELINE)
# ==============================================================================
st.sidebar.header("🔍 Filter Options")

# --- Filter 1: Target Antigen ---
antigens = ["All"] + sorted(ANTIGEN_LIST)
selected_ant = st.sidebar.selectbox("Select Target Antigen:", options=antigens)

# Step 1 Subsetting: Filter dataset by Antigen to populate Indication options dynamically
if selected_ant != "All":
    df_antigen_filtered = filter_trials(df, target=selected_ant)
else:
    df_antigen_filtered = df.copy()

# --- Filter 2: Cancer Indication ---
indications = ["All"] + sorted(
    [str(i) for i in df_antigen_filtered["Indication"].dropna().unique()]
)
selected_ind = st.sidebar.selectbox(
    "Select Cancer Indication:", options=indications
)

# Step 2 Subsetting: Apply Indication filter directly on the Antigen-filtered subset
ind_filter = None if selected_ind == "All" else selected_ind
filtered_df = filter_trials(df_antigen_filtered, indication=ind_filter)

# Summary banner for active filter combination
st.markdown(
    f"Showing **{len(filtered_df)}** trials for Antigen: **{selected_ant}** |"
    f" Indication: **{selected_ind}**"
)
st.divider()

# ==============================================================================
# 3. KPI METRICS CARDS
# ==============================================================================
if not filtered_df.empty:
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)

    # Metric 1: Total Volume
    total_trials = len(filtered_df)
    col_m1.metric(label="Total Trials", value=f"{total_trials:,}")

    # Metric 2: Commercial Share
    industry_count = len(
        filtered_df[filtered_df["Sponsor Type"] == "Industry"]
    )
    industry_pct = (
        (industry_count / total_trials * 100) if total_trials > 0 else 0
    )
    col_m2.metric(label="Industry Share", value=f"{industry_pct:.1f}%")

    # Metric 3: Geographic Leader
    valid_countries = filtered_df[filtered_df["Main Country"] != "Unknown"][
        "Main Country"
    ]
    top_country = (
        valid_countries.mode()[0] if not valid_countries.empty else "N/A"
    )
    display_country = top_country.replace("United States", "USA").replace("United Kingdom", "UK")
    col_m3.metric(label="Top Country", value=display_country)

    # Metric 4: Primary Clinical Phase
    valid_phases = filtered_df[filtered_df["Phase"] != "Not Applicable"][
        "Phase"
    ]
    top_phase = valid_phases.mode()[0] if not valid_phases.empty else "N/A"
    col_m4.metric(label="Dominant Phase", value=top_phase)

    st.divider()

    # ==========================================================================
    # 4. CHART GENERATION (PLOTLY EXPRESS)
    # ==========================================================================

    # --- Chart 1: Temporal Growth (Line Chart) ---
    yearly_df = filtered_df[
        filtered_df["Start Year"].notna() & (filtered_df["Start Year"] > 2005)
    ]
    yearly_counts = yearly_df["Start Year"].value_counts().reset_index()
    yearly_counts.columns = ["Start Year", "Count"]
    yearly_counts = yearly_counts.sort_values("Start Year")

    fig_years = px.line(
        yearly_counts,
        x="Start Year",
        y="Count",
        title="Trial Growth Over Time",
        markers=True,
        template="plotly_white",
    )
    fig_years.update_layout(title_x=0.5)

    # --- Chart 2: Sponsor Breakdown (Donut Chart) ---
    sponsor_counts = filtered_df["Sponsor Type"].value_counts().reset_index()
    sponsor_counts.columns = ["Sponsor Type", "Count"]

    fig_sponsor = px.pie(
        sponsor_counts,
        names="Sponsor Type",
        values="Count",
        hole=0.4,
        title="Sponsor Types",
        template="plotly_white",
    )
    fig_sponsor.update_layout(
        title_x=0.5, legend=dict(orientation="h", y=-0.2)
    )

    # --- Chart 3: Phase Distribution (Horizontal Bar Chart) ---
    is_not_applicable = filtered_df["Phase"].isin(["NOT APPLICABLE", "Not Applicable"])
    valid_phases_df = filtered_df[~is_not_applicable]

    # Chronological phase sorting via Phase Order column
    phase_counts = (
        valid_phases_df.groupby(["Phase", "Phase Order"])
        .size()
        .reset_index(name="Count")
        .sort_values("Phase Order", ascending=False)
    )

    fig_phase = px.bar(
        phase_counts,
        x="Count",
        y="Phase",
        orientation="h",
        title="Clinical Trial Phases",
        template="plotly_white",
    )
    fig_phase.update_layout(
        title_x=0.5,
        xaxis_title="Number of Trials",
        yaxis_title="",
    )

    # --- Chart 4: Top Geographic Regions (Horizontal Bar Chart) ---
    country_counts = (
        filtered_df[filtered_df["Main Country"] != "Unknown"]["Main Country"]
        .value_counts()
        .head(8)
        .reset_index()
    )
    country_counts.columns = ["Country", "Count"]

    fig_country = px.bar(
        country_counts,
        x="Count",
        y="Country",
        orientation="h",
        title="Top Countries",
        template="plotly_white",
    )
    fig_country.update_layout(
        title_x=0.5,
        xaxis_title="Number of Trials",
        yaxis_title="",
        yaxis={"categoryorder": "total ascending"},
    )

    # ==========================================================================
    # 5. DASHBOARD GRID LAYOUT (2x2 MATRIX)
    # ==========================================================================
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(fig_years, width="stretch")
    with col2:
        st.plotly_chart(fig_sponsor, width="stretch")

    col3, col4 = st.columns(2)
    with col3:
        st.plotly_chart(fig_phase, width="stretch")
    with col4:
        st.plotly_chart(fig_country, width="stretch")

else:
    # Fallback state for empty filter results
    st.warning("No clinical trials match the selected filter combination.")

# ==============================================================================
# 6. RAW DATA INSPECTION TABLE
# ==============================================================================
st.divider()
st.subheader("📋 Raw Trial Details")

st.dataframe(
    filtered_df[[
        "NCT ID",
        "Title",
        "Target Antigen",
        "Indication",
        "Phase",
        "Status",
        "Sponsor",
        "Main Country",
        "Start Year",
        "Link"
    ]],
    width="stretch",
    hide_index=True,
    column_config={
        "Link": st.column_config.LinkColumn(
            "Link",
            display_text="Open Trial 🔗",
            width="medium",
        ),
    },
)