
import pandas as pd
import requests
import streamlit as st
import plotly.express as px


# HEADLINE ---
st.title("🛡️ CAR-T Cell Therapy Dashboard")
st.caption(
    "Real-time analytical breakdown of CAR-T clinical trials from ClinicalTrials.gov database"
)

# ANTIGEN LIST ---
antigens_list = [
    "CD19", "BCMA", "CD20", "CD22", "CD30", "CD123", "CD33", "GPRC5D",  # Hematological
    "HER2", "MSLN", "GD2", "PSMA", "EGFR", "CLAUDIN", "CLDN18.2"  # Solid tumors
]

# RUN SEARCH BUTTON ---
selected_ant = st.selectbox('Choose target antigen for detailed analysis:',
                                    options=antigens_list)

run_search = st.button('Press to run the analysis')

if run_search:
    query_intervention = "CAR-T"
    url = f"https://clinicaltrials.gov/api/v2/studies?query.intr={query_intervention}&pageSize=500"

    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        clean_data = []


        for study in data.get("studies", []):
            protocol = study.get("protocolSection", {})
            ident = protocol.get("identificationModule", {})
            status = protocol.get("statusModule", {})
            design = protocol.get("designModule", {})
            sponsor = protocol.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
            title = ident.get("briefTitle", "N/A")

            for antigen in antigens_list:
                if antigen in title.upper():
                    target_antigen = antigen
                    break
            else:
                target_antigen = "Other"

            clean_data.append({
                "NCT ID": ident.get("nctId", "N/A"),
                "Title": title,
                "Target Antigen": target_antigen,
                "Status": status.get("overallStatus", "N/A"),
                "Phase": ", ".join(design.get("phases", ["NA"])),
                "Sponsor Type": sponsor.get("class", "N/A"),
            })

        df = pd.DataFrame(clean_data)
        filtered_df = df[df["Target Antigen"] == selected_ant]
        st.success(f"Successfully loaded {len(df)} trials!\n")
    else:
        st.write(f"Failed to fetch data. Status code: {response.status_code}")
        st.stop()




    #GRAPHS ---

    # GENERAL PI CHART
    wo_others = df[df["Target Antigen"] != "Other"]

    fig_all_antigens = px.pie(
        wo_others,
        names="Target Antigen",
        title="Overall Target Antigen Landscape"
    )
    st.plotly_chart(fig_all_antigens)


    col1, col2 = st.columns(2)
    # DIFFERENT PHASES GRAPH
    phase_counts = filtered_df["Phase"].value_counts().reset_index()
    phase_counts.columns = ["Phase", "Count"]

    fig_phase = px.bar(
        phase_counts,
        x="Count",
        y="Phase",
        orientation="h",
        title= f'Clinical Trial Phases for {selected_ant} Antigen'
    )
    fig_phase.update_traces(width = 0.4)
    col1.plotly_chart(fig_phase)


    # SPONSOR CHART
    sponsor_counts = filtered_df["Sponsor Type"].value_counts().reset_index()
    sponsor_counts.columns = ["Sponsor Type", "Count"]

    sponsor_map = {
        "OTHER": "Academic / Hospital",
        "INDUSTRY": "Pharma / Industry",
        "OTHER_GOV": "Government",
        "FED": "Federal Agency",
        "NETWORK": "Research Network",
    }
    sponsor_counts["Sponsor Type"] = sponsor_counts["Sponsor Type"].replace(sponsor_map)

    fig_sponsor = px.pie(
        sponsor_counts,
        names="Sponsor Type",
        values="Count",
        hole=0.5,
        title=f' Sponsor Types for {selected_ant} Antigen'
    )

    col2.plotly_chart(fig_sponsor)



