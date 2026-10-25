"""
eligibility.py — Feature 3 backend logic for SchemeSetu.

Fast keyword/regex-based eligibility filtering over the scheme CSV.
No LLM calls. Deliberately over-inclusive: if a scheme's eligibility text
doesn't explicitly mention an age range, income ceiling, or a specific state,
the filter does NOT exclude it — it's included so the user can read the real
eligibility text and judge for themselves ("benefit of the doubt").

Central-level schemes always pass the state filter (they apply nationwide by
definition); only State-level schemes are checked against the user's selected
state, and only if a state name was actually found in that scheme's text.
"""

import re
from pathlib import Path

import pandas as pd

CSV_PATH = Path(__file__).resolve().parent / "data" / "updated_data.csv"

# ---------------------------------------------------------------------------
# Static reference data
# ---------------------------------------------------------------------------

STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand", "Karnataka",
    "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur", "Meghalaya",
    "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan", "Sikkim",
    "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh", "Uttarakhand",
    "West Bengal",
    # Union Territories
    "Andaman and Nicobar Islands", "Chandigarh",
    "Dadra and Nagar Haveli and Daman and Diu", "Delhi", "Jammu and Kashmir",
    "Ladakh", "Lakshadweep", "Puducherry",
]

CATEGORY_KEYWORDS = {
    "farmer": [
        "farmer", "farmers", "agricultur", "cultivator", "kisan", "farming",
        "crop", "irrigation", "horticulture", "dairy farmer", "fisherm",
        "fisherwom",
    ],
    "student": [
        "student", "students", "scholarship", "school", "college",
        "university", "education", "academic", "pupil", "learner",
    ],
    "woman": [
        "woman", "women", "girl", "mother", "widow", "pregnant",
        "lactating", "self help group", "self-help group", "shg",
        "maternity",
    ],
    "senior_citizen": [
        "senior citizen", "old age", "elderly", "pension", "aged",
        "above 60", "above 65", "60 years and above",
    ],
    "person_with_disability": [
        "disability", "disabled", "differently abled", "divyang",
        "handicapped", "specially abled", "pwd",
    ],
    "unemployed": [
        "unemployed", "unemployment", "jobless", "job seeker",
        "job-seeker", "seeking employment", "out of work",
    ],
    "bpl_low_income": [
        "below poverty line", "bpl", "low income", "economically weaker",
        "ews", "poor family", "poverty", "antyodaya", "destitute",
    ],
}

CATEGORY_LABELS = {
    "farmer": "Farmer",
    "student": "Student",
    "woman": "Woman",
    "senior_citizen": "Senior Citizen",
    "person_with_disability": "Person with Disability",
    "unemployed": "Unemployed",
    "bpl_low_income": "BPL / Low Income",
}


# ---------------------------------------------------------------------------
# Document vocabulary (6.5) -- free-text `documents` column -> small fixed set
# ---------------------------------------------------------------------------
# Keyword matching on lower-cased text. Extend a list (or add a key) and the
# planner picks it up; nothing else needs to change. Keep keywords specific:
# "caste" alone would match half the CSV, "caste certificate" will not.

DOCUMENT_KEYWORDS = {
    "aadhaar": ["aadhaar", "aadhar", "adhar", "uidai"],
    "income_certificate": [
        "income certificate", "income proof", "proof of income",
        "income declaration", "income statement", "salary certificate",
    ],
    "caste_certificate": [
        "caste certificate", "caste proof", "community certificate",
        "caste validity", "sc/st certificate", "obc certificate",
        "tribe certificate", "tribal certificate",
    ],
    "ration_card": ["ration card", "pds card", "food security card"],
    "bank_passbook": [
        "passbook", "bank account", "bank details", "cancelled cheque",
        "canceled cheque", "bank statement",
        "ifsc", "account number", "account no",
    ],
    "domicile": [
        "domicile", "residence certificate", "residence proof",
        "proof of residence", "resident certificate", "address proof",
        "proof of address", "nativity",
        "utility bill", "electricity bill", "water bill",
        "telephone bill", "rent agreement",
    ],
    "age_proof": [
        "age proof", "proof of age", "birth certificate", "date of birth",
        "school leaving", "age certificate",
    ],
    "land_records": [
        "land record", "land document", "khasra", "khatauni", "7/12",
        "patta", "land ownership", "record of rights", "land holding",
        "landholding", "jamabandi",
    ],
    "disability_certificate": [
        "disability certificate", "udid", "disability card",
        "handicap certificate", "pwd certificate", "divyang certificate",
    ],
    "bpl_card": [
        "bpl card", "bpl certificate", "below poverty line", "antyodaya",
        "bpl",
    ],
    "voter_id": ["voter id", "voter card", "election card"],
    "pan_card": ["pan card", "pan number"],
    "driving_license": ["driving license", "driving licence"],
    "photo": ["photograph", "passport size", "passport-size", "passport photo"],
    "marksheet": ["marksheet", "mark sheet", "mark-sheet"],
}

DOCUMENT_LABELS = {
    "aadhaar": "Aadhaar card",
    "income_certificate": "Income certificate",
    "caste_certificate": "Caste certificate",
    "ration_card": "Ration card",
    "bank_passbook": "Bank passbook / account details",
    "domicile": "Domicile / residence proof",
    "age_proof": "Age proof",
    "land_records": "Land records",
    "disability_certificate": "Disability certificate",
    "bpl_card": "BPL card",
    "voter_id": "Voter ID",
    "pan_card": "PAN card",
    "driving_license": "Driving licence",
    "photo": "Passport-size photograph",
    "marksheet": "Class 10th/12th marksheet",
}

# ---------------------------------------------------------------------------
# Life events (6.6) -- same mechanism as CATEGORY_KEYWORDS: keyword bundles
# matched against scheme text. Curated by hand; edit freely.
# ---------------------------------------------------------------------------

LIFE_EVENTS = {
    "new_baby": {
        "label": "Had a baby / expecting",
        "keywords": [
            "maternity", "pregnan", "lactating", "newborn", "new born",
            "infant", "childbirth", "child birth", "institutional delivery",
            "janani", "mother and child",
        ],
    },
    "lost_job": {
        "label": "Lost my job",
        "keywords": [
            "unemployed", "unemployment", "jobless", "retrench",
            "job loss", "job seeker", "job-seeker", "skill training",
            "skill development", "rozgar", "placement",
        ],
    },
    "start_business": {
        "label": "Starting a business",
        "keywords": [
            "entrepreneur", "startup", "start-up", "self employment",
            "self-employment", "msme", "micro enterprise", "business loan",
            "mudra", "credit guarantee", "stand-up", "own business",
        ],
    },
    "daughter_marriage": {
        "label": "Daughter's marriage",
        "keywords": [
            "marriage", "wedding", "kanyadan", "shaadi", "vivah",
            "girl child", "kanya", "mass marriage",
        ],
    },
    "retiring": {
        "label": "Retiring / old age",
        "keywords": [
            "pension", "old age", "senior citizen", "elderly", "retire",
            "superannuation", "annuity",
        ],
    },
    "child_education": {
        "label": "Child starting school or college",
        "keywords": [
            "scholarship", "education loan", "tuition", "fee reimbursement",
            "stipend", "school fee", "higher education",
        ],
    },
    "health_emergency": {
        "label": "Medical emergency / serious illness",
        "keywords": [
            "medical treatment", "hospitalisation", "hospitalization",
            "health insurance", "critical illness", "ayushman",
            "cancer", "dialysis", "medical assistance",
        ],
    },
    "crop_loss": {
        "label": "Crop loss / natural calamity",
        "keywords": [
            "crop insurance", "crop loss", "drought", "flood",
            "natural calamity", "crop damage", "calamity",
        ],
    },
}

EVENT_LABELS = {k: v["label"] for k, v in LIFE_EVENTS.items()}

# ---------------------------------------------------------------------------
# Regex patterns for age / income extraction
# ---------------------------------------------------------------------------

# "18 to 60 years", "18-60 years", "between 18 and 60 years"
_AGE_RANGE_RE = re.compile(
    r"(\d{1,3})\s*(?:to|-|–|and)\s*(\d{1,3})\s*years",
    re.IGNORECASE,
)
# "above 60 years", "over 60 years", "minimum age of 18 years", "at least 18 years"
_AGE_ABOVE_RE = re.compile(
    r"(?:above|over|minimum age(?:\s+of)?|at least|not less than)\s*(\d{1,3})\s*years",
    re.IGNORECASE,
)
# "below 35 years", "under 35 years", "maximum age of 35 years", "not exceeding 35 years"
_AGE_BELOW_RE = re.compile(
    r"(?:below|under|maximum age(?:\s+of)?|not exceeding|up to)\s*(\d{1,3})\s*years",
    re.IGNORECASE,
)

# "income should not exceed ₹1,50,000", "income less than Rs. 2,00,000",
# "income up to ₹ 3,00,000", "annual family income ... ₹96,000"
_INCOME_RE = re.compile(
    r"income[^.]{0,60}?(?:not\s+exceed|less\s+than|up\s+to|below|within|should\s+not\s+be\s+more\s+than)"
    r"[^.\d]{0,20}(?:₹|rs\.?|inr)?\s*([\d,]{3,})",
    re.IGNORECASE,
)

_STATE_LOOKUP = [(s, s.lower()) for s in STATES]


def _extract_age_range(text: str):
    """Return (age_min, age_max) tuple; either may be None."""
    if not text:
        return None, None

    m = _AGE_RANGE_RE.search(text)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return (a, b) if a <= b else (b, a)

    age_min, age_max = None, None
    m_above = _AGE_ABOVE_RE.search(text)
    if m_above:
        age_min = int(m_above.group(1))
    m_below = _AGE_BELOW_RE.search(text)
    if m_below:
        age_max = int(m_below.group(1))

    return age_min, age_max


def _extract_income_ceiling(text: str):
    if not text:
        return None
    m = _INCOME_RE.search(text)
    if not m:
        return None
    raw = m.group(1).replace(",", "")
    try:
        return int(raw)
    except ValueError:
        return None


# Older / alternative spellings that appear in scheme text.
_STATE_ALIASES = {
    "orissa": "Odisha",
    "pondicherry": "Puducherry",
    "uttaranchal": "Uttarakhand",
}


def _extract_states(text: str):
    """States named in `text`. If more than one is named the text is
    ambiguous, so return [] (benefit of the doubt) rather than guess.

    "&" is read as "and", because the data writes "Jammu & Kashmir" and
    "Andaman & Nicobar Islands" while STATES uses "and"; without this those
    schemes looked state-less and passed the filter for every state."""
    if not text:
        return []
    lowered = re.sub(r"\s+", " ", text.lower().replace("&", " and "))
    found = {s for s, s_lower in _STATE_LOOKUP if s_lower in lowered}
    found |= {canon for alias, canon in _STATE_ALIASES.items() if alias in lowered}
    if len(found) > 1:
        return []
    return sorted(found)


def _extract_documents(text: str):
    """Document keys (from DOCUMENT_KEYWORDS) mentioned in the free-text
    `documents` column, as a frozenset. Empty set = nothing recognised."""
    if not text:
        return frozenset()
    lowered = text.lower()
    return frozenset(
        key for key, words in DOCUMENT_KEYWORDS.items()
        if any(w in lowered for w in words)
    )


# ---------------------------------------------------------------------------
# DataFrame loading / caching
# ---------------------------------------------------------------------------

_df_cache = None


def _text_col(df, name):
    """Return text column `name` as clean strings; blank if the column is missing."""
    if name in df.columns:
        return df[name].fillna("").astype(str)
    return pd.Series([""] * len(df), index=df.index)


def load_dataframe(force_reload: bool = False):
    """Load the CSV once, cache in memory, precompute filter fields.
    Pass force_reload=True (the admin Reindex does) to re-read the CSV."""
    global _df_cache
    if _df_cache is not None and not force_reload:
        return _df_cache

    df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")

    # Normalize text columns we depend on so downstream code never sees NaN.
    for col in ["scheme_name", "slug", "level", "eligibility", "details",
                "schemeCategory", "tags", "benefits", "application", "documents"]:
        df[col] = _text_col(df, col)

    elig_text = df["eligibility"]

    ages = elig_text.map(_extract_age_range)
    df["_age_min"] = ages.map(lambda t: t[0])
    df["_age_max"] = ages.map(lambda t: t[1])

    df["_income_ceiling"] = elig_text.map(_extract_income_ceiling)

    state_scan_text = elig_text + " " + df["details"] + " " + df["application"]
    df["_states_mentioned"] = state_scan_text.map(_extract_states)

    df["_category_text"] = (
        df["schemeCategory"] + " " + df["tags"] + " " + df["eligibility"]
    ).str.lower()

    # 6.5: which of the known documents each scheme asks for
    df["_documents"] = df["documents"].map(_extract_documents)

    # 6.6: high-signal text for life-event ranking (name + category + tags)
    df["_head_text"] = (df["scheme_name"] + " " + df["schemeCategory"] + " " + df["tags"]).str.lower()

    _df_cache = df
    return _df_cache


# ---------------------------------------------------------------------------
# Row-level filter predicates
# ---------------------------------------------------------------------------

# Each _check_* returns (passes, reason). `reason` is None when the scheme is
# excluded; otherwise a dict the UI shows under "Why this matched":
#   {field, status: matched|unverified|na, code, params, note}
# `code` + `params` let the frontend render the sentence in any language;
# `note` is the same sentence in English (fallback / API consumers).
#   matched    - the scheme text states a constraint and the user satisfies it
#   unverified - the text states no constraint, so it was kept on benefit of the
#                doubt and the user must verify it themselves
#   na         - the user did not provide this input, so it was not applied

_NOTES = {
    "age_na": "Age not provided",
    "age_unverified": "No age limit found in the scheme text — verify yourself",
    "age_range": "Age {age} is within {min}–{max}",
    "age_min": "Age {age} meets the minimum age of {min}",
    "age_max": "Age {age} is within the maximum age of {max}",
    "income_na": "Income not provided",
    "income_unverified": "No income limit found in the scheme text — verify yourself",
    "income_ceiling": "Income ₹{income} is within the limit of ₹{ceiling}",
    "state_na": "State not provided",
    "state_central": "Central scheme — applies across India",
    "state_match": "Scheme text mentions {state}",
    "state_unverified": "No specific state found in the scheme text — verify yourself",
    "category_na": "Category not provided",
    "category_match": "Matches {category} (found \u201c{keyword}\u201d in the scheme text)",
    "event_match": "Related to \u201c{event}\u201d (found \u201c{keyword}\u201d in the scheme text)",
}


def _inr(n):
    """Indian digit grouping: 1500000 -> 15,00,000."""
    digits = str(int(n))
    if len(digits) <= 3:
        return digits
    head, tail = digits[:-3], digits[-3:]
    groups = []
    while len(head) > 2:
        groups.insert(0, head[-2:])
        head = head[:-2]
    if head:
        groups.insert(0, head)
    return ",".join(groups + [tail])


def _reason(field, status, code, **params):
    shown = {k: (_inr(v) if k in ("income", "ceiling") else v) for k, v in params.items()}
    note = _NOTES[code]
    if params:
        note = note.format(**shown)
    return {"field": field, "status": status, "code": code, "params": params, "note": note}


def _check_age(row, age):
    if age is None:
        return True, _reason("age", "na", "age_na")
    age_min, age_max = row["_age_min"], row["_age_max"]
    has_min, has_max = pd.notna(age_min), pd.notna(age_max)
    if not has_min and not has_max:
        return True, _reason("age", "unverified", "age_unverified")  # benefit of the doubt
    if has_min and age < age_min:
        return False, None
    if has_max and age > age_max:
        return False, None
    if has_min and has_max:
        return True, _reason("age", "matched", "age_range", age=int(age), min=int(age_min), max=int(age_max))
    if has_min:
        return True, _reason("age", "matched", "age_min", age=int(age), min=int(age_min))
    return True, _reason("age", "matched", "age_max", age=int(age), max=int(age_max))


def _check_income(row, income):
    if income is None:
        return True, _reason("income", "na", "income_na")
    ceiling = row["_income_ceiling"]
    if pd.isna(ceiling):
        return True, _reason("income", "unverified", "income_unverified")  # benefit of the doubt
    if income > ceiling:
        return False, None
    return True, _reason("income", "matched", "income_ceiling", income=int(income), ceiling=int(ceiling))


def _check_state(row, state):
    if state is None:
        return True, _reason("state", "na", "state_na")
    if row.get("level") == "Central":
        return True, _reason("state", "matched", "state_central")  # applies nationwide
    states_mentioned = row["_states_mentioned"]
    if not states_mentioned:
        return True, _reason("state", "unverified", "state_unverified")  # benefit of the doubt
    if state not in states_mentioned:
        return False, None
    return True, _reason("state", "matched", "state_match", state=state)


def _check_category(row, category):
    if category is None:
        return True, _reason("category", "na", "category_na")
    keywords = CATEGORY_KEYWORDS.get(category, [])
    if not keywords:
        return True, _reason("category", "na", "category_na")
    category_text = row["_category_text"]
    for kw in keywords:
        if kw in category_text:
            return True, _reason("category", "matched", "category_match", category=category, keyword=kw)
    return False, None


def _event_score(row, event):
    """(score, first_keyword) for a life event. Hits in the scheme's name /
    category / tags count 3x; hits in the eligibility text count 1x.
    Score 0 means no keyword was found."""
    spec = LIFE_EVENTS.get(event)
    if not spec:
        return 0, None
    head, body = row["_head_text"], row["_category_text"]
    score, first = 0, None
    for kw in spec["keywords"]:
        in_head, in_body = kw in head, kw in body
        if in_head or in_body:
            score += 3 if in_head else 1
            first = first or kw
    return score, first


def _check_event(row, event):
    if event is None or event not in LIFE_EVENTS:
        return True, None
    score, kw = _event_score(row, event)
    if score == 0:
        return False, None
    return True, _reason("event", "matched", "event_match",
                         event=LIFE_EVENTS[event]["label"], keyword=kw)


# Thin wrappers kept so existing callers/tests that import these still work.
def _row_matches_age(row, age):
    return _check_age(row, age)[0]


def _row_matches_income(row, income):
    return _check_income(row, income)[0]


def _row_matches_state(row, state):
    return _check_state(row, state)[0]


def _row_matches_category(row, category):
    return _check_category(row, category)[0]


def explain_row(row, age=None, income=None, state=None, category=None, event=None):
    """The reasons for a row (age, income, state, category, plus the life event
    when one was chosen), or None if the row is excluded. Uses the same checks
    as the filter, so what the card says can never disagree with why the
    scheme was included."""
    checks = [
        _check_age(row, age),
        _check_income(row, income),
        _check_state(row, state),
        _check_category(row, category),
    ]
    if event in LIFE_EVENTS:
        checks.append(_check_event(row, event))
    reasons = []
    for passes, reason in checks:
        if not passes:
            return None
        reasons.append(reason)
    return reasons


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

def _snippet(text: str, length: int = 220) -> str:
    text = (text or "").strip()
    if len(text) <= length:
        return text
    return text[:length].rsplit(" ", 1)[0] + "..."


def _match_frame(age=None, income=None, state=None, category=None, event=None):
    """The rows that pass every provided filter. When a life event is given the
    rows are ordered best-match first (stable, so ties keep CSV order)."""
    df = load_dataframe()
    event = event if event in LIFE_EVENTS else None

    mask = df.apply(
        lambda row: (
            _row_matches_age(row, age)
            and _row_matches_income(row, income)
            and _row_matches_state(row, state)
            and _row_matches_category(row, category)
            and (event is None or _check_event(row, event)[0])
        ),
        axis=1,
    )
    matched = df[mask]
    if event is not None and len(matched):
        scores = matched.apply(lambda r: _event_score(r, event)[0], axis=1)
        matched = matched.loc[scores.sort_values(ascending=False, kind="stable").index]
    return matched


def _display_state(row):
    """Which single state a state-level scheme belongs to, for the result card.
    Display only (the filter does not use it). Tries the scheme name first
    ("West Bengal Transport Workers..."), then the states named in its text;
    "" when none or several are named."""
    name_states = _extract_states(str(row.get("scheme_name", "")))
    if len(name_states) == 1:
        return name_states[0]
    mentioned = row.get("_states_mentioned") or []
    return mentioned[0] if len(mentioned) == 1 else ""


def filter_schemes(age=None, income=None, state=None, category=None, limit=25, event=None):
    """
    Apply all filters (each skip-if-not-provided) and return matched schemes
    with the total count and a capped, trimmed list of results.
    `event` is an optional LIFE_EVENTS key (6.6).
    """
    matched = _match_frame(age, income, state, category, event)
    total = len(matched)

    results = []
    for _, row in matched.head(limit).iterrows():
        results.append({
            "reasons": explain_row(row, age=age, income=income, state=state,
                                   category=category, event=event) or [],
            "scheme_name": row.get("scheme_name", ""),
            "slug": row.get("slug", ""),
            "apply_url": f"{MYSCHEME_BASE}/{row.get('slug')}" if row.get("slug") else None,
            "level": row.get("level", ""),
            "state": _display_state(row),
            "category": row.get("schemeCategory", ""),
            "eligibility_snippet": _snippet(row.get("eligibility", "")),
            "benefits_snippet": _snippet(row.get("benefits", "")),
            "documents_needed": [
                {"key": key, "label": DOCUMENT_LABELS[key]}
                for key in sorted(row["_documents"], key=lambda k: DOCUMENT_LABELS[k])
            ],
            "documents_note": _snippet(row.get("documents", ""), length=320),
        })

    return {
        "total_matched": total,
        "returned": len(results),
        "matches": results,
    }


def _plan_from_rows(rows, have=None, example_limit=3):
    """Shared by plan_documents and plan_documents_for_names: `rows` is an
    iterable of scheme rows (each with a precomputed `_documents` set)."""
    rows = list(rows)
    have_set = {k for k in (have or []) if k in DOCUMENT_KEYWORDS}

    needed_by = {k: 0 for k in DOCUMENT_KEYWORDS}
    unlocks = {k: [] for k in DOCUMENT_KEYWORDS}
    ready_now = 0
    docs_unknown = 0

    for row in rows:
        docs = row["_documents"]
        if not docs:
            docs_unknown += 1
            continue
        for d in docs:
            needed_by[d] += 1
        missing = docs - have_set
        if not missing:
            ready_now += 1
        elif len(missing) == 1:
            unlocks[next(iter(missing))].append(row.get("scheme_name", ""))

    documents = [
        {
            "key": k,
            "label": DOCUMENT_LABELS[k],
            "needed_by": needed_by[k],
            "unlocks": len(unlocks[k]),
            "unlock_examples": unlocks[k][:example_limit],
            "have": k in have_set,
        }
        for k in DOCUMENT_KEYWORDS
        if needed_by[k] > 0
    ]
    documents.sort(key=lambda d: (-d["needed_by"], d["label"]))

    return {
        "total_schemes": len(rows),
        "ready_now": ready_now,
        "docs_unknown": docs_unknown,
        "documents": documents,
    }


def plan_documents(age=None, income=None, state=None, category=None, event=None,
                   have=None, example_limit=3):
    """Document readiness planner (6.5).

    Runs the same filter as /eligibility, then looks at which known documents
    each matching scheme asks for. `have` is a list of document keys the user
    already holds.

      needed_by  schemes (among the matches) that list this document
      unlocks    schemes whose ONLY missing document is this one -- i.e.
                 getting it makes them ready to apply for
      ready_now  schemes that list at least one known document and whose
                 documents the user already has
      docs_unknown  schemes whose `documents` text mentions none of the
                 known documents (kept, not blocked; the user should read it)
    """
    matched = _match_frame(age, income, state, category, event)
    return _plan_from_rows((row for _, row in matched.iterrows()), have, example_limit)


_PAGE_SUFFIX_RE = re.compile(r"\s*\(page [^)]*\)\s*$", re.IGNORECASE)


def plan_documents_for_names(names, have=None, example_limit=3):
    """Document planner for specific schemes, e.g. the sources of a chat answer.

    `names` are scheme names or slugs; a trailing "(page N)" (how /ask labels
    its sources) is ignored. Unknown names are skipped. Zero LLM calls."""
    df = load_dataframe()
    by_name = {}
    for _, row in df.iterrows():
        by_name.setdefault(str(row["scheme_name"]).strip().lower(), row)
        slug = str(row["slug"]).strip().lower()
        if slug:
            by_name.setdefault(slug, row)

    rows, seen = [], set()
    for raw in names or []:
        key = _PAGE_SUFFIX_RE.sub("", str(raw)).strip().lower()
        row = by_name.get(key)
        if row is not None and key not in seen:
            seen.add(key)
            rows.append(row)
    return _plan_from_rows(rows, have, example_limit)


MYSCHEME_BASE = "https://www.myscheme.gov.in/schemes"


def data_updated():
    """Date (YYYY-MM-DD) the scheme CSV was last written: the initial scrape, or
    the latest admin edit/upload. Shown to users as "data as of"."""
    import datetime as _dt
    try:
        return _dt.date.fromtimestamp(CSV_PATH.stat().st_mtime).isoformat()
    except OSError:
        return None


def scheme_links(names):
    """Official-page info for scheme names (e.g. a chat answer's sources).
    Returns {input string: {name, slug, url, level}}; unknown names are omitted."""
    df = load_dataframe()
    by_name = {}
    for _, row in df.iterrows():
        by_name.setdefault(str(row["scheme_name"]).strip().lower(), row)
        slug = str(row["slug"]).strip().lower()
        if slug:
            by_name.setdefault(slug, row)
    out = {}
    for raw in names or []:
        row = by_name.get(_PAGE_SUFFIX_RE.sub("", str(raw)).strip().lower())
        if row is None:
            continue
        slug = str(row["slug"]).strip()
        out[raw] = {
            "name": row["scheme_name"],
            "slug": slug,
            "url": f"{MYSCHEME_BASE}/{slug}" if slug else None,
            "level": row.get("level", ""),
        }
    return out


def get_scheme_rows(slugs):
    """Rows for the given slugs, in the order asked (unknown slugs skipped).
    Used by verify.py."""
    df = load_dataframe()
    by_slug = {r["slug"]: r for _, r in df.iterrows()}
    return [by_slug[s] for s in slugs if s in by_slug]
