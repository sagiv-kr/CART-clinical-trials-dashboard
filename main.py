from datetime import date
from pathlib import Path
import base64
import math

import pandas as pd
import plotly.express as px
import streamlit as st
from cart_data import ANTIGEN_LIST, filter_trials, get_available_indications, get_trials

LOGO_PATH = Path(__file__).parent / "logo.png"
LOGO_DATA_URI = (
    "data:image/png;base64,"
    + base64.b64encode(LOGO_PATH.read_bytes()).decode("ascii")
)

# ClinicalTrials.gov country names -> ISO-3 codes for the bubble map.
COUNTRY_TO_ISO3 = {
    "United States": "USA",
    "China": "CHN",
    "Germany": "DEU",
    "France": "FRA",
    "United Kingdom": "GBR",
    "Italy": "ITA",
    "Spain": "ESP",
    "Canada": "CAN",
    "Japan": "JPN",
    "Korea, Republic of": "KOR",
    "Australia": "AUS",
    "Netherlands": "NLD",
    "Belgium": "BEL",
    "Switzerland": "CHE",
    "Israel": "ISR",
    "Poland": "POL",
    "Sweden": "SWE",
    "Austria": "AUT",
    "Denmark": "DNK",
    "Norway": "NOR",
    "Finland": "FIN",
    "Brazil": "BRA",
    "India": "IND",
    "Singapore": "SGP",
    "Taiwan": "TWN",
    "Hong Kong": "HKG",
    "Russian Federation": "RUS",
    "Mexico": "MEX",
    "Argentina": "ARG",
    "Turkey": "TUR",
    "Greece": "GRC",
    "Portugal": "PRT",
    "Ireland": "IRL",
    "Czech Republic": "CZE",
    "Czechia": "CZE",
    "Hungary": "HUN",
    "Romania": "ROU",
    "Ukraine": "UKR",
    "South Africa": "ZAF",
    "New Zealand": "NZL",
    "Thailand": "THA",
    "Malaysia": "MYS",
    "Egypt": "EGY",
    "Chile": "CHL",
    "Colombia": "COL",
    "Saudi Arabia": "SAU",
    "United Arab Emirates": "ARE",
    "Pakistan": "PAK",
    "Bangladesh": "BGD",
    "Philippines": "PHL",
    "Indonesia": "IDN",
    "Vietnam": "VNM",
    "Viet Nam": "VNM",
    "Nigeria": "NGA",
    "Kenya": "KEN",
    "Morocco": "MAR",
    "Tunisia": "TUN",
    "Lebanon": "LBN",
    "Jordan": "JOR",
    "Serbia": "SRB",
    "Croatia": "HRV",
    "Slovenia": "SVN",
    "Slovakia": "SVK",
    "Bulgaria": "BGR",
    "Lithuania": "LTU",
    "Latvia": "LVA",
    "Estonia": "EST",
    "Iceland": "ISL",
    "Luxembourg": "LUX",
    "Georgia": "GEO",
    "Armenia": "ARM",
    "Kazakhstan": "KAZ",
    "Belarus": "BLR",
    "Peru": "PER",
    "Ecuador": "ECU",
    "Uruguay": "URY",
    "Costa Rica": "CRI",
    "Panama": "PAN",
    "Puerto Rico": "PRI",
    "Iran, Islamic Republic of": "IRN",
    "Iraq": "IRQ",
    "Algeria": "DZA",
    "Ghana": "GHA",
    "Uganda": "UGA",
    "Tanzania, United Republic of": "TZA",
    "Ethiopia": "ETH",
    "Bosnia and Herzegovina": "BIH",
    "North Macedonia": "MKD",
    "Albania": "ALB",
    "Moldova, Republic of": "MDA",
    "Cyprus": "CYP",
    "Malta": "MLT",
    "Qatar": "QAT",
    "Kuwait": "KWT",
    "Oman": "OMN",
    "Bahrain": "BHR",
    "Sri Lanka": "LKA",
    "Nepal": "NPL",
    "Cambodia": "KHM",
    "Myanmar": "MMR",
    "Macao": "MAC",
}

# ==============================================================================
# 1. PAGE CONFIGURATION & DATA INITIALIZATION
# ==============================================================================
st.set_page_config(
    page_title="CAR-T Clinical Trial Landscape",
    page_icon=str(LOGO_PATH),
    layout="wide",
)
st.markdown(
    """
    <style>
    div[data-testid="stImage"] img { border-radius: 50%; }
    div[data-testid="stImage"] button { display: none; }
    section[data-testid="stSidebar"] [data-testid="stImage"] {
        display: flex;
        justify-content: center;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Load clinical trial dataset
df = get_trials()

# Page Header
logo_col, title_col = st.columns([1, 12], vertical_alignment="center")
with logo_col:
    st.image(str(LOGO_PATH), width=88)
with title_col:
    st.title("CAR-T Clinical Trial Landscape")

# ==============================================================================
# 2. SIDEBAR FILTERS (SEQUENTIAL FILTERING PIPELINE)
# ==============================================================================
st.sidebar.markdown(
    f"""
    <div style="display:flex;justify-content:center;margin:0.4rem 0 0.8rem;">
        <img src="{LOGO_DATA_URI}" alt="CAR-T Clinical Trial Landscape logo"
             width="200" style="border-radius:50%;display:block;" />
    </div>
    """,
    unsafe_allow_html=True,
)
st.sidebar.header("🔍 Filter Options")

# --- Filter 1: Target Antigen ---
antigens = ["All"] + sorted(ANTIGEN_LIST)
selected_ant = st.sidebar.selectbox("Select Target Antigen:", options=antigens)
antigen_filter = None if selected_ant == "All" else selected_ant

# --- Filter 2: Cancer Indication ---
# Options come from get_available_indications so the menu only lists
# indications that exist for the selected antigen.
indications = ["All"] + [
    str(i)
    for i in get_available_indications(df, antigen_filter)
    if pd.notna(i)
]
selected_ind = st.sidebar.selectbox(
    "Select Cancer Indication:", options=indications
)

ind_filter = None if selected_ind == "All" else selected_ind
filtered_df = filter_trials(df, target=antigen_filter, indication=ind_filter)

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
    col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)

    # Metric 1: Total Volume
    total_trials = len(filtered_df)
    col_m1.metric(label="Total Trials", value=f"{total_trials:,}")

    # Metric 2: Currently Recruiting
    recruiting_count = int((filtered_df["Status"] == "Recruiting").sum())
    col_m2.metric(label="Currently Recruiting", value=f"{recruiting_count:,}")

    # Metric 3: Commercial Share
    industry_count = len(
        filtered_df[filtered_df["Sponsor Type"] == "Industry"]
    )
    industry_pct = (
        (industry_count / total_trials * 100) if total_trials > 0 else 0
    )
    col_m3.metric(label="Industry Share", value=f"{industry_pct:.1f}%")

    # Metric 4: Geographic Leader
    valid_countries = filtered_df[filtered_df["Main Country"] != "Unknown"][
        "Main Country"
    ]
    top_country = (
        valid_countries.mode()[0] if not valid_countries.empty else "N/A"
    )
    display_country = top_country.replace("United States", "USA").replace("United Kingdom", "UK")
    col_m4.metric(label="Top Country", value=display_country)

    # Metric 5: Primary Clinical Phase
    valid_phases = filtered_df[filtered_df["Phase"] != "Not Applicable"][
        "Phase"
    ]
    top_phase = valid_phases.mode()[0] if not valid_phases.empty else "N/A"
    col_m5.metric(label="Dominant Phase", value=top_phase)

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
    today = date.today()
    today_year = today.year + (today.timetuple().tm_yday - 1) / 365.25
    fig_years.add_vline(
        x=today_year,
        line_dash="dot",
        line_color="gray",
        line_width=2,
        annotation_text="Today",
        annotation_position="top",
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

    # --- Chart 4: Geographic Distribution (Country Bubbles) ---
    country_counts = (
        filtered_df[filtered_df["Main Country"] != "Unknown"]["Main Country"]
        .value_counts()
        .reset_index()
    )
    country_counts.columns = ["Country", "Count"]
    country_counts["iso_alpha"] = country_counts["Country"].map(COUNTRY_TO_ISO3)
    country_counts = country_counts.dropna(subset=["iso_alpha"])
    
    if country_counts.empty:
        country_counts["pixel_size"] = pd.Series(dtype=float)
    else:
        log_count = country_counts["Count"].map(math.log10)
        log_span = float(log_count.max() - log_count.min())
        if log_span == 0:
            country_counts["pixel_size"] = 12.0
        else:
            country_counts["pixel_size"] = (
                8 + 12 * (log_count - log_count.min()) / log_span
            )

    fig_country = px.scatter_geo(
        country_counts,
        locations="iso_alpha",
        color="Count",
        hover_name="Country",
        hover_data={"iso_alpha": False, "Count": True, "pixel_size": False},
        projection="natural earth",
        title="Trials by Country",
        template="plotly_white",
        color_continuous_scale=[
            [0.0, "#fc9272"],
            [0.5, "#ef3b2c"],
            [1.0, "#99000d"],
        ],
    )
    if not country_counts.empty:
        fig_country.update_traces(
            marker=dict(
                size=country_counts["pixel_size"].tolist(),
                sizemode="diameter",
                sizeref=1,
                opacity=0.75,
                line=dict(width=0.8, color="white"),
            )
        )
    fig_country.update_geos(
        showcountries=True,
        showcoastlines=True,
        showland=True,
        landcolor="rgb(243, 243, 243)",
        countrycolor="rgb(204, 204, 204)",
        showframe=False,
    )
    fig_country.update_layout(
        title_x=0.5,
        margin=dict(l=0, r=0, t=50, b=0),
        coloraxis_colorbar=dict(title="Trials"),
        height=450,
    )

    # --- Chart 5: Trial Status (Horizontal Bar Chart) ---
    status_order = [
        "Not yet recruiting",
        "Recruiting",
        "Enrolling by invitation",
        "Active, not recruiting",
        "Completed",
        "Suspended",
        "Terminated",
        "Withdrawn",
        "Unknown status",
    ]
    status_colors = {
        "Not yet recruiting": "#FF7F0E",
        "Recruiting": "#1F77B4",
        "Enrolling by invitation": "#1F77B4",
        "Active, not recruiting": "#2CA02C",
        "Completed": "#7F8C8D",
        "Suspended": "#D62728",
        "Terminated": "#D62728",
        "Withdrawn": "#D62728",
        "Unknown status": "#C7C7C7",
    }
    status_counts = filtered_df["Status"].value_counts().reset_index()
    status_counts.columns = ["Status", "Count"]
    present_statuses = [
        status for status in status_order if status in set(status_counts["Status"])
    ]
    extra_statuses = [
        status
        for status in status_counts["Status"]
        if status not in present_statuses
    ]
    for status in extra_statuses:
        status_colors.setdefault(status, "#C7C7C7")
    ordered_statuses = present_statuses + extra_statuses

    fig_status = px.bar(
        status_counts,
        x="Count",
        y="Status",
        orientation="h",
        title="Trial Status",
        template="plotly_white",
        color="Status",
        color_discrete_map=status_colors,
        category_orders={"Status": ordered_statuses},
    )
    fig_status.update_layout(
        title_x=0.5,
        xaxis_title="Number of Trials",
        yaxis_title="",
        showlegend=False,
        yaxis={
            "categoryorder": "array",
            "categoryarray": list(reversed(ordered_statuses)),
        },
    )

    # ==========================================================================
    # 5. DASHBOARD GRID LAYOUT
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
        st.plotly_chart(fig_status, width="stretch")

    st.plotly_chart(fig_country, width="stretch")

else:
    # Fallback state for empty filter results
    st.warning("No clinical trials match the selected filter combination.")

# ==============================================================================
# 6. RAW DATA INSPECTION TABLE
# ==============================================================================
st.divider()
st.subheader("Clinical Trials")

search_term = st.text_input(
    "Search trials",
    placeholder="Search any keyword across all fields",
)
table_df = filtered_df
if search_term.strip():
    query = search_term.strip()
    match_any_field = pd.Series(False, index=filtered_df.index)
    for column in filtered_df.columns:
        match_any_field = match_any_field | filtered_df[column].fillna("").astype(
            str
        ).str.contains(query, case=False, regex=False)
    table_df = filtered_df[match_any_field]

if search_term.strip():
    st.caption(f"{len(table_df):,} matching trials")

st.dataframe(
    table_df[[
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
    use_container_width=True,
    hide_index=True,
    column_config={
        "Link": st.column_config.LinkColumn(
            "Link",
            display_text="Open Trial 🔗",
            width="medium",
        ),
    },
)
