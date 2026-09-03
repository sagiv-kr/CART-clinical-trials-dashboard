# Data layer - how the CAR-T trial data is built

Everything about the data lives in three files:

| File | What it is |
| --- | --- |
| `cart_data.py` | the code: download, extract, filter, classify, clean |
| `data/car_t_targets.json` | curated list: which CAR-T product / antigen name belongs to which target |
| `data/indication_groups.json` | curated list: which condition keywords belong to which cancer indication |
| `data/cart_trials.csv` | the finished table (created by the code, so the app starts fast) |

## How to use it in the Streamlit app

```python
from cart_data import get_trials, filter_trials, get_available_indications, ANTIGEN_LIST

df = get_trials()                                    # the clean table
indications = get_available_indications(df, "CD19")  # only what exists for CD19
trials = filter_trials(df, target="CD19", indication="Lymphoma")
```

`get_trials()` reads `data/cart_trials.csv` if it exists. `get_trials(refresh=True)`
downloads everything again from ClinicalTrials.gov and saves a new CSV.

To update the data by hand, run:

```bash
python cart_data.py
```

## Columns in the table

| Column | Notes |
| --- | --- |
| `NCT ID`, `Title`, `Link` | `Link` opens the study on ClinicalTrials.gov |
| `Target Antigen` | `"CD19"`, or `"CD19, CD22"` for a dual CAR-T, or `"Unknown"` |
| `Number of Targets` | 2 or more means a dual / multi-target CAR-T |
| `Indication` | Multiple Myeloma, Leukemia, Lymphoma, Autoimmune Disease, Solid Tumor, Other Blood Cancer, Other |
| `Phase`, `Phase Order` | `Phase Order` is a number, for sorting graphs and finding the highest phase |
| `Status` | Recruiting, Completed, Terminated ... |
| `Sponsor`, `Sponsor Type` | Industry / Academic / Hospital / Government ... |
| `Interventions`, `Conditions` | the original free text, for the trial table |
| `Enrollment`, `Start Year` | numbers, good for "patients enrolled" and "trials per year" |
| `Main Country`, `Countries` | where the trial runs |

## The two filtering stages (the main idea of the project)

**Stage 1 - broad API search (high recall).**
We send `query.intr=CAR-T OR "chimeric antigen receptor"` to the
ClinicalTrials.gov API. We do *not* search for `CD19` here: that would also
return CD19 antibodies and bispecifics, which are not CAR-T at all.

**What `query.intr` actually searches (important distinction).**

The parameter maps to ClinicalTrials.gov's **InterventionSearch area**, which
covers about 12 related fields, including:

* `InterventionName`, `InterventionOtherName`, `InterventionDescription`
* `ArmGroupLabel`, `ArmGroupDescription`
* `BriefTitle`, `OfficialTitle`
* `Keyword`, MeSH terms, and intervention type codes

So a trial can appear in Stage 1 because "CAR-T" is in the **title** or
**keywords**, even when the listed intervention is something else. That is why
Stage 2 exists.

For comparison:

| API parameter | What it searches |
| --- | --- |
| `query.intr` | InterventionSearch area (~12 intervention-related fields) |
| `query.term` | Full-text across all study fields |
| Neither | Every trial in the registry |

The download follows `nextPageToken` until there are no more pages, up to a
cap of 10 pages × 1000 studies = **10 000 trials**. The current result count is
well below that cap.

**Stage 2 - our own classification (high precision).**
We read the Intervention/Treatment text of every downloaded study and decide
ourselves whether it is a CAR-T trial and which target it uses.

The funnel (numbers from the last run):

| Step | Trials |
| --- | --- |
| returned by the broad search | 2676 |
| have a real CAR-T intervention | 1834 |
| also interventional (not a registry / observational study) | **1788** |
| target antigen identified | 1162 |
| more than one target | 233 |

## Why the classification is done on the interventions and not on the title

Real examples from the data:

* `NCT02601313` - intervention is `brexucabtagene autoleucel`. The word CD19 does
  not appear anywhere, but our curated file knows this product is CD19.
* `NCT06918912` - a study of `Loncastuximab Tesirine`, an anti-CD19
  antibody-drug conjugate, in patients after CAR-T failure. The title contains
  both "CD19" and "CAR-T", but it is not a CAR-T trial. Removed.
* `NCT04822974` - title is "TORQUETENOVIRUS IN CAR-T THERAPY". The only
  intervention is `blood collection`. Removed.
* `NCT06464679` - `anti-CD19 CAR NK cells`. Same receptor idea, but NK cells and
  not T cells. Removed.

## Cleaning steps we can talk about in the presentation

1. **Pagination** - the API answers in pages of up to 1000, so we follow
   `nextPageToken` until the end (max 10 pages = 10 000 studies). Without
   pagination we would only see the first page.
2. **Only the fields we need** - the request sends a `fields` list, so we get a
   small answer instead of the full study record.
3. **Nested JSON** - interventions, conditions and locations are lists inside
   dictionaries inside `protocolSection`.
4. **Two matching rules** - a curated product name is enough on its own, but an
   antigen name only counts when the intervention also looks like a CAR-T.
5. **Word matching instead of `in`** - `"CD3" in text` would also be true for
   "CD30" and "CD33", so we use a small regular expression instead.
6. **CAR-T naming variants** - `CAR-T`, `CAR T`, `CART19`, `4SCAR-GD2`,
   `CD19 CAR engineered T cells`, `chimeric antigen receptor`, and the official
   drug ending `-cabtagene` (axicabtagene, idecabtagene, rapcabtagene ...).
7. **Dual CAR-T** - a trial can have two targets, so `Target Antigen` can be
   `"CD19, CD22"` and `filter_trials` checks membership instead of equality.
8. **Grouping free text conditions** - "Diffuse Large B-Cell Lymphoma",
   "Non-Hodgkin Lymphoma" and "B-Cell Lymphoma" all become `Lymphoma`.
   Only about 4% of trials stay in `Other`.
9. **Autoimmune disease group** - the data shows CAR-T is now also tested in
   lupus, systemic sclerosis and other autoimmune diseases, so this deserved
   its own group instead of being hidden inside "Other".
10. **Code to text** - `ACTIVE_NOT_RECRUITING` becomes "Active, not recruiting",
    `["PHASE1","PHASE2"]` becomes "Phase 1/2", `OTHER` becomes
    "Academic / Hospital".
11. **Small text problems** - HTML codes (`Sjogren&#39;s`), double spaces,
    duplicated intervention names, empty values, duplicate NCT IDs.
12. **Saving the result** - the clean table is written to CSV, so the app does
    not download 2676 studies on every click.

## Known limits (good answer for a question after the presentation)

* About one third of the CAR-T trials only write `CAR-T cells` in the
  intervention field and never say which antigen they target. We label these
  `Unknown` instead of guessing.
* A few trials use an internal code we do not know (`FT819`, `AMG 553`), so
  their target stays `Unknown` until we add it to the curated file.
* Trials that never write "CAR" anywhere in the intervention field, for example
  `Human BCMA Targeted T Cells Injection`, are missed by stage 2.
