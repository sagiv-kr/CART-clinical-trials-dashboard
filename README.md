# CAR-T Clinical Trial Landscape

An interactive Streamlit dashboard of the CAR-T clinical-trial landscape, built from [ClinicalTrials.gov](https://clinicaltrials.gov/) data.

Researchers, biotech teams, and students can select a **target antigen** (for example CD19 or BCMA) and a **cancer indication** (for example lymphoma or multiple myeloma) and see how crowded, mature, and geographically concentrated that slice of development is.

Data are retrieved with a broad ClinicalTrials.gov search, then classified using curated lists of CAR-T products and cancer-condition keywords. The dashboard updates its metrics, charts, and trial table from those filters.

## Streamlit link

- **Local app:** [http://localhost:8501](http://localhost:8501)
- **Hosted app:** [https://cart-clinical-trials-dashboard-dgn9rjbwqwxhefa3unxndf.streamlit.app/](https://cart-clinical-trials-dashboard-dgn9rjbwqwxhefa3unxndf.streamlit.app/)

## What the dashboard shows

After you choose a target and an indication, the page shows:

- KPI cards: total trials, currently recruiting, industry share, top country, and dominant phase
- Trial growth over time
- Sponsor types
- Clinical-trial phases
- Trial status
- Geographic distribution by country
- A table of matching studies, with keyword search and links back to ClinicalTrials.gov

## How to run

**File to execute:** `main.py`

Python 3.11 or newer is required. Install dependencies with Poetry (preferred) or pip.

### Poetry

```bash
poetry install
poetry run streamlit run main.py
```

### pip

```bash
pip install -r requirements.txt
streamlit run main.py
```

The app opens in the browser at [http://localhost:8501](http://localhost:8501).

On first run, if `data/cart_trials.csv` is not present, the app downloads trials from ClinicalTrials.gov. Later launches reuse the saved CSV.

To rebuild that table from the API:

```bash
python cart_data.py
```

## Project layout

| File | Role |
| --- | --- |
| `main.py` | Streamlit dashboard (run this file) |
| `logo.png` | App logo (required; used in the sidebar, header, and browser tab) |
| `cart_data.py` | Download, classify, and clean trial data |
| `data/car_t_targets.json` | Curated CAR-T product → antigen map |
| `data/indication_groups.json` | Condition keywords → indication groups |
| `pyproject.toml` / `poetry.lock` | Poetry dependencies |
| `requirements.txt` | pip dependencies |
