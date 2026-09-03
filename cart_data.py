"""
CAR-T Clinical Trial Landscape Explorer - data layer.

This file does all the work with the data:
    1. asks the ClinicalTrials.gov API for CAR-T trials (broad search = high recall)
    2. reads the important fields out of the nested JSON answer
    3. decides which trials are really CAR-T trials and which target antigen they use
    4. groups the messy condition names into a few cancer indications
    5. cleans the phase / status / sponsor values and returns a tidy pandas DataFrame

The Streamlit app only needs one line:

    from cart_data import get_trials
    df = get_trials()

Run this file on its own (python cart_data.py) to download the data and print a
short report about every cleaning step.
"""

import html
import json
import os
import re

import pandas as pd
import requests


# ---------------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------------

API_URL = "https://clinicaltrials.gov/api/v2/studies"

# First filtering stage: a wide search inside the Intervention/Treatment field.
# We ask for two spellings because many academic trials write the full words
# "chimeric antigen receptor" and never write "CAR-T".
# (We do NOT search for the antigen name here - "CD19" would also return
# antibodies and bispecifics that are not CAR-T at all.)
SEARCH_QUERY = 'CAR-T OR "chimeric antigen receptor"'

# We only ask the API for the fields we actually use, so the answer stays small.
API_FIELDS = [
    "NCTId",
    "BriefTitle",
    "OverallStatus",
    "StartDate",
    "Phase",
    "StudyType",
    "EnrollmentCount",
    "LeadSponsorName",
    "LeadSponsorClass",
    "Condition",
    "InterventionName",
    "LocationCountry",
]

# Where our curated files and the saved table live.
DATA_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
TARGETS_FILE = os.path.join(DATA_FOLDER, "car_t_targets.json")
INDICATIONS_FILE = os.path.join(DATA_FOLDER, "indication_groups.json")
CACHE_FILE = os.path.join(DATA_FOLDER, "cart_trials.csv")

# Nicer names for the codes that the API returns.
PHASE_NAMES = {
    "EARLY_PHASE1": "Early Phase 1",
    "PHASE1": "Phase 1",
    "PHASE2": "Phase 2",
    "PHASE3": "Phase 3",
    "PHASE4": "Phase 4",
    "NA": "Not Applicable",
}

# A number for every phase, so the app can sort the graph and find the
# highest phase a target has reached.
PHASE_ORDER = {
    "Not Applicable": 0,
    "Early Phase 1": 1,
    "Phase 1": 2,
    "Phase 1/2": 3,
    "Phase 2": 4,
    "Phase 2/3": 5,
    "Phase 3": 6,
    "Phase 4": 7,
}

STATUS_NAMES = {
    "RECRUITING": "Recruiting",
    "NOT_YET_RECRUITING": "Not yet recruiting",
    "ENROLLING_BY_INVITATION": "Enrolling by invitation",
    "ACTIVE_NOT_RECRUITING": "Active, not recruiting",
    "COMPLETED": "Completed",
    "SUSPENDED": "Suspended",
    "TERMINATED": "Terminated",
    "WITHDRAWN": "Withdrawn",
    "UNKNOWN": "Unknown status",
}

SPONSOR_NAMES = {
    "INDUSTRY": "Industry",
    "OTHER": "Academic / Hospital",
    "OTHER_GOV": "Government",
    "FED": "Federal Agency",
    "NIH": "NIH",
    "NETWORK": "Research Network",
    "INDIV": "Individual",
}


# ---------------------------------------------------------------------------
# 1. READING OUR CURATED FILES
# ---------------------------------------------------------------------------

def load_json_file(path):
    """Read one of our JSON files and drop the keys that are only explanations."""
    with open(path, "r", encoding="utf-8") as file:
        content = json.load(file)

    clean_content = {}
    for key in content:
        # keys that start with "_" (like "_comment") are notes for humans
        if not key.startswith("_"):
            clean_content[key] = content[key]
    return clean_content


TARGETS = load_json_file(TARGETS_FILE)
INDICATION_GROUPS = load_json_file(INDICATIONS_FILE)

# The antigens the user can choose in the app.
ANTIGEN_LIST = list(TARGETS.keys())
INDICATION_LIST = list(INDICATION_GROUPS.keys()) + ["Other"]


# ---------------------------------------------------------------------------
# 2. DOWNLOADING THE TRIALS FROM THE API
# ---------------------------------------------------------------------------

def fetch_studies(query=SEARCH_QUERY, page_size=1000, max_pages=10):
    """
    Download all studies that match the broad search.

    The API sends the results in pages. Every answer contains a
    "nextPageToken", and we have to send that token back to get the next page.
    Without this loop we would only see the first page and silently lose trials.
    """
    studies = []
    page_token = None

    for page in range(max_pages):
        params = {
            "query.intr": query,
            "pageSize": page_size,
            "fields": ",".join(API_FIELDS),
        }
        if page_token:
            params["pageToken"] = page_token

        response = requests.get(API_URL, params=params, timeout=60)
        response.raise_for_status()
        answer = response.json()

        studies = studies + answer.get("studies", [])

        page_token = answer.get("nextPageToken")
        if not page_token:
            break  # no more pages, we have everything

    return studies


# ---------------------------------------------------------------------------
# 3. TAKING THE FIELDS WE NEED OUT OF THE NESTED JSON
# ---------------------------------------------------------------------------

def tidy(text):
    """
    Clean one piece of free text that came from the API.

    Some studies contain HTML codes instead of real characters, for example
    "Sjogren&#39;s Syndrome" instead of "Sjogren's Syndrome", and some have
    double spaces or line breaks inside the name.
    """
    text = html.unescape(text)
    return " ".join(text.split())


def read_one_study(study):
    """Turn one nested study from the API into one flat dictionary."""
    protocol = study.get("protocolSection", {})
    identification = protocol.get("identificationModule", {})
    status = protocol.get("statusModule", {})
    design = protocol.get("designModule", {})
    sponsor = protocol.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
    conditions_module = protocol.get("conditionsModule", {})
    arms_module = protocol.get("armsInterventionsModule", {})
    locations_module = protocol.get("contactsLocationsModule", {})

    # The interventions are a list of small dictionaries, we only want the names.
    # A few studies write the same intervention twice, so we keep it only once.
    interventions = []
    for item in arms_module.get("interventions", []):
        name = item.get("name")
        if name and tidy(name) not in interventions:
            interventions.append(tidy(name))

    conditions = []
    for condition in conditions_module.get("conditions", []):
        conditions.append(tidy(condition))

    # Every location is one hospital, so the same country appears many times.
    countries = []
    for location in locations_module.get("locations", []):
        country = location.get("country")
        if country and country not in countries:
            countries.append(country)

    return {
        "NCT ID": identification.get("nctId", ""),
        "Title": tidy(identification.get("briefTitle", "")),
        "Interventions": interventions,
        "Conditions": conditions,
        "Phase": design.get("phases", []),
        "Study Type": design.get("studyType", ""),
        "Enrollment": design.get("enrollmentInfo", {}).get("count"),
        "Status": status.get("overallStatus", ""),
        "Start Date": status.get("startDateStruct", {}).get("date", ""),
        "Sponsor": tidy(sponsor.get("name", "")),
        "Sponsor Type": sponsor.get("class", ""),
        "Countries": countries,
    }


# ---------------------------------------------------------------------------
# 4. SECOND FILTERING STAGE - IS THIS REALLY A CAR-T TRIAL, AND WHICH TARGET?
# ---------------------------------------------------------------------------

# How sponsors write a CAR-T product inside the Intervention field:
#   "car[\s\-_]?t(?![a-z])"      -> CAR-T, CAR T, CART19, huCART19
#   "cars?(?![a-z])"             -> CAR alone: "CD19 CAR engineered T cells", "EGFRvIII-CARs"
#   "chimeric antigen receptor"  -> the words written in full
#   "cabtagene"                  -> every official CAR-T drug name ends like this
#                                   (tisagenlecleucel is older, but axicabtagene,
#                                    idecabtagene, rapcabtagene ... all share it)
# The (?![a-z]) parts are important: they stop the pattern from finding "car"
# inside normal words such as "cartilage", "carboplatin" or "carcinoma".
CAR_T_PATTERN = re.compile(
    r"car[\s\-_]?t(?![a-z])|cars?(?![a-z])|chimeric antigen receptor|cabtagene",
    re.IGNORECASE,
)

# CAR-NK cells and CAR-macrophages use the same receptor idea but a different
# cell type, so they are not CAR-T trials and we do not want them.
OTHER_CAR_CELLS_PATTERN = re.compile(r"car[\s\-_]?(nk|nkt|m)\b", re.IGNORECASE)


def looks_like_car_t(text):
    """True if this intervention text describes a CAR-T cell product."""
    if OTHER_CAR_CELLS_PATTERN.search(text):
        return False
    return CAR_T_PATTERN.search(text) is not None


def mentions_antigen(text, antigen):
    """
    True if the antigen name appears in the text as its own "word".

    We need this because a simple "CD19 in text" would also be True for
    "CD193", and "CD3" would be found inside "CD30" and "CD33".
    Letters are allowed directly after the name, so "CD19CAR" still matches.
    """
    pattern = r"(?<![a-z0-9])" + re.escape(antigen.lower()) + r"(?![0-9])"
    return re.search(pattern, text.lower()) is not None


def find_targets(interventions):
    """
    Look at the Intervention/Treatment names of one study and return the list
    of CAR-T targets it uses, for example ["CD19"] or ["CD19", "CD22"].

    Two different rules, on purpose:
      * a product name from our curated file is enough on its own
        ("brexucabtagene autoleucel" never says CD19, but we know it is CD19)
      * an antigen name only counts when the same intervention also looks like
        a CAR-T ("Anti-CD19 CAR-T cells" counts, "Blinatumomab" does not)

    The targets are always returned in the order of our JSON file, so a dual
    CAR-T is always written "CD19, CD22" and never "CD22, CD19".
    """
    found = []

    for target in TARGETS:
        matched = False

        for intervention in interventions:
            text = intervention.lower()

            for product in TARGETS[target]["products"]:
                if product.lower() in text:
                    matched = True

            if looks_like_car_t(intervention):
                for antigen in TARGETS[target]["antigen_names"]:
                    if mentions_antigen(intervention, antigen):
                        matched = True

        if matched:
            found.append(target)

    return found


def is_car_t_trial(interventions, targets):
    """
    True if at least one intervention is a CAR-T product.

    This is what removes the studies that the broad search brings in only
    because CAR-T is mentioned as background - for example a trial of
    tocilizumab for cytokine release syndrome *after* CAR-T therapy. Such a
    study lists only "Tocilizumab" as its intervention, so it is dropped here.
    """
    for intervention in interventions:
        if looks_like_car_t(intervention):
            return True

    # A trial that only lists a brand name ("Kymriah") is still a CAR-T trial.
    return len(targets) > 0


# ---------------------------------------------------------------------------
# 5. GROUPING THE CANCER INDICATIONS
# ---------------------------------------------------------------------------

def find_indication(conditions):
    """
    Put the free text conditions of a study into one broad group.

    "Diffuse Large B-Cell Lymphoma", "Non-Hodgkin Lymphoma" and
    "B-Cell Lymphoma" should all end up as one group: Lymphoma.
    """
    text = " ; ".join(conditions).lower()

    # The groups are checked in the order they appear in the JSON file.
    for group in INDICATION_GROUPS:
        for keyword in INDICATION_GROUPS[group]:
            if keyword in text:
                return group

    return "Other"


# ---------------------------------------------------------------------------
# 6. SMALL CLEANING HELPERS
# ---------------------------------------------------------------------------

def clean_phase(phases):
    """Turn the list of phase codes into one readable value."""
    if not phases:
        return "Not Applicable"

    # A trial can be registered in two phases at the same time.
    if phases == ["PHASE1", "PHASE2"]:
        return "Phase 1/2"
    if phases == ["PHASE2", "PHASE3"]:
        return "Phase 2/3"

    return PHASE_NAMES.get(phases[0], phases[0])


def clean_start_year(start_date):
    """The API gives "2019-08-14" or sometimes only "2019". We want the year."""
    if not start_date:
        return None
    return int(start_date[:4])


def clean_text(value, default="Unknown"):
    """Remove extra spaces and replace an empty value."""
    if not value:
        return default
    return value.strip()


# ---------------------------------------------------------------------------
# 7. BUILDING THE TABLE
# ---------------------------------------------------------------------------

def build_table(studies):
    """
    Turn the raw studies into a DataFrame.

    Nothing is removed here. We only add the columns that say what we think
    about every study, so we can count later how many studies each filtering
    step removes.
    """
    rows = []

    for study in studies:
        row = read_one_study(study)
        targets = find_targets(row["Interventions"])

        row["Is CAR-T Trial"] = is_car_t_trial(row["Interventions"], targets)
        row["Target Antigen"] = ", ".join(targets) if targets else "Unknown"
        row["Number of Targets"] = len(targets)
        row["Indication"] = find_indication(row["Conditions"])

        row["Phase"] = clean_phase(row["Phase"])
        row["Phase Order"] = PHASE_ORDER.get(row["Phase"], 0)
        row["Status"] = STATUS_NAMES.get(row["Status"], "Unknown status")
        row["Sponsor"] = clean_text(row["Sponsor"])
        row["Sponsor Type"] = SPONSOR_NAMES.get(row["Sponsor Type"], "Other")
        row["Start Year"] = clean_start_year(row["Start Date"])

        # Lists are not comfortable inside a table or a CSV file, so we join them.
        row["Main Country"] = row["Countries"][0] if row["Countries"] else "Unknown"
        row["Interventions"] = clean_text(", ".join(row["Interventions"]), "Not reported")
        row["Conditions"] = clean_text(", ".join(row["Conditions"]), "Not reported")
        row["Countries"] = clean_text(", ".join(row["Countries"]), "Not reported")

        row["Link"] = "https://clinicaltrials.gov/study/" + row["NCT ID"]
        rows.append(row)

    return pd.DataFrame(rows)


def clean_table(df):
    """Keep only the studies we want to analyse and tidy the table."""
    # The same NCT ID should never appear twice.
    df = df.drop_duplicates(subset="NCT ID")

    # Second filtering stage: a real CAR-T intervention is required.
    df = df[df["Is CAR-T Trial"]]

    # Observational studies and patient registries have no phase and are not
    # part of the clinical development landscape we want to show.
    df = df[df["Study Type"] == "INTERVENTIONAL"]

    df = df.sort_values("Start Year", ascending=False)
    return df.reset_index(drop=True)


# ---------------------------------------------------------------------------
# 8. THE FUNCTIONS THE APP USES
# ---------------------------------------------------------------------------

def get_trials(refresh=False):
    """
    Return the clean table of CAR-T trials.

    The table is saved to data/cart_trials.csv, so the app does not have to
    download 2500+ studies again every time. Use refresh=True for fresh data.
    """
    if not refresh and os.path.exists(CACHE_FILE):
        return pd.read_csv(CACHE_FILE)

    studies = fetch_studies()
    df = clean_table(build_table(studies))
    df.to_csv(CACHE_FILE, index=False)
    return df


def filter_trials(df, target=None, indication=None):
    """
    Filter the table for the choices of the user.

    We cannot simply write df["Target Antigen"] == "CD19", because a trial of a
    dual CAR-T is saved as "CD19, CD22" and belongs to both targets.
    """
    if target:
        keep = []
        for value in df["Target Antigen"]:
            keep.append(target in value.split(", "))
        df = df[keep]

    if indication:
        df = df[df["Indication"] == indication]

    return df


def get_available_indications(df, target):
    """The indications that really exist for this target, for the second menu."""
    trials = filter_trials(df, target=target)
    return sorted(trials["Indication"].unique())


# ---------------------------------------------------------------------------
# 9. RUNNING THIS FILE DIRECTLY - DOWNLOAD THE DATA AND SHOW WHAT HAPPENED
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Downloading trials from ClinicalTrials.gov ...")
    studies = fetch_studies()
    print("Studies returned by the broad search:", len(studies))

    full_table = build_table(studies)
    clean = clean_table(full_table)

    print("Studies with a real CAR-T intervention:", int(full_table["Is CAR-T Trial"].sum()))
    print("After also keeping only interventional studies:", len(clean))
    print("Of those, target antigen identified:", len(clean[clean["Target Antigen"] != "Unknown"]))
    print("Trials with more than one target:", len(clean[clean["Number of Targets"] > 1]))

    print("\nTrials per target antigen:")
    print(clean["Target Antigen"].value_counts().head(10))

    print("\nTrials per indication:")
    print(clean["Indication"].value_counts())

    clean.to_csv(CACHE_FILE, index=False)
    print("\nSaved", len(clean), "trials to", CACHE_FILE)
