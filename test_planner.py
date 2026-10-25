"""
test_planner.py -- tests for 6.5 (document planner), 6.6 (life events) and
6.7 (LLM-verified shortlist). Needs no internet, FAISS or Gemini key:
rag_chat and admin are replaced by stubs, and a small synthetic CSV is used.

Run from the folder that holds app.py:   python test_planner.py
"""
import sys
import types
import tempfile
from pathlib import Path

import pandas as pd

# ---- stubs so app.py imports without FAISS / Gemini ------------------------
class LLMError(Exception):
    def __init__(self, kind, message):
        super().__init__(message)
        self.kind = kind

GEMINI_REPLY = {"text": "[]", "raise": None}

def fake_ask_gemini(prompt):
    GEMINI_REPLY["last_prompt"] = prompt
    if GEMINI_REPLY["raise"]:
        raise GEMINI_REPLY["raise"]
    return GEMINI_REPLY["text"]

rag = types.ModuleType("rag_chat")
rag.LANGUAGES = {"en": "English"}
rag.LLMError = LLMError
rag.ask_gemini = fake_ask_gemini
rag.answer_question_full = lambda *a, **k: {}
rag.load_index = lambda: object()
rag.normalise_language = lambda l: l
rag.translate_text = lambda t, l: t
sys.modules["rag_chat"] = rag

adm = types.ModuleType("admin")
class AdminError(Exception): pass
adm.AdminError = AdminError
sys.modules["admin"] = adm

import eligibility  # noqa: E402

ROWS = [
    # name, slug, level, category, tags, eligibility, details, application, documents, benefits
    ("Kisan Aadhaar Scheme", "kisan-aadhaar", "Central", "Agriculture", "farmer",
     "Farmers aged 18 to 60 years with income not exceeding Rs 1,50,000.", "", "",
     "Aadhaar card, bank passbook, land records", "Rs 6000 per year"),
    ("Maternity Support", "maternity-support", "Central", "Health", "women, maternity",
     "Pregnant and lactating women.", "", "",
     "Aadhaar card, bank passbook", "Cash support"),
    ("Aadhaar Only Pension", "aadhaar-only-pension", "Central", "Social welfare", "pension, senior citizen",
     "Senior citizens above 60 years.", "", "",
     "Aadhaar", "Monthly pension"),
    ("Kerala Student Aid", "kerala-student-aid", "State", "Education", "student, scholarship",
     "Students of Kerala. Income should not exceed Rs 2,00,000.", "Kerala government", "",
     "Aadhaar card, income certificate, caste certificate", "Scholarship"),
    ("Mystery Scheme", "mystery", "Central", "Misc", "farmer",
     "Farmers.", "", "", "Photo and application form only", "Help"),
    ("MUDRA Starter", "mudra-starter", "Central", "Business", "entrepreneur, msme",
     "Entrepreneurs aged 18 to 65 years starting a micro enterprise.", "", "",
     "Aadhaar, bank account details, domicile certificate", "Loan"),
    ("Empty Docs Scheme", "empty-docs", "Central", "Agriculture", "farmer",
     "Farmers.", "", "", "", "Help"),
]
COLS = ["scheme_name", "slug", "level", "schemeCategory", "tags", "eligibility",
        "details", "application", "documents", "benefits"]
tmp = Path(tempfile.mkdtemp()) / "data.csv"
pd.DataFrame(ROWS, columns=COLS).to_csv(tmp, index=False)
eligibility.CSV_PATH = tmp
eligibility.load_dataframe(force_reload=True)

passed = failed = 0
def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  {detail}")

# ---------------------------------------------------------------- 6.5 vocab
print("\n6.5 document vocabulary")
ex = eligibility._extract_documents
check("Aadhaar spellings", ex("Adhar card") == {"aadhaar"} and ex("AADHAAR") == {"aadhaar"})
check("several documents", ex("Aadhaar card, bank passbook, land records") == {"aadhaar", "bank_passbook", "land_records"})
check("nothing recognised -> empty", ex("Photo and application form only") == frozenset())
check("empty text -> empty", ex("") == frozenset())
check("bare 'caste' does not match", ex("Applicants from any caste may apply") == frozenset())
df = eligibility.load_dataframe()
check("_documents column exists", "_documents" in df.columns)

# ---------------------------------------------------------------- 6.5 planner
print("\n6.5 planner")
plan = eligibility.plan_documents()
byk = {d["key"]: d for d in plan["documents"]}
check("all schemes counted", plan["total_schemes"] == 7)
check("docs_unknown counts rows with no known docs", plan["docs_unknown"] == 2, plan["docs_unknown"])
check("aadhaar needed by 5", byk["aadhaar"]["needed_by"] == 5, byk["aadhaar"]["needed_by"])
check("sorted by needed_by desc", [d["needed_by"] for d in plan["documents"]] == sorted([d["needed_by"] for d in plan["documents"]], reverse=True))
check("aadhaar unlocks only 'Aadhaar Only Pension'",
      byk["aadhaar"]["unlocks"] == 1 and byk["aadhaar"]["unlock_examples"] == ["Aadhaar Only Pension"], byk["aadhaar"])
check("nothing ready with no documents", plan["ready_now"] == 0)

plan2 = eligibility.plan_documents(have=["aadhaar"])
b2 = {d["key"]: d for d in plan2["documents"]}
check("have=aadhaar -> ready_now 1", plan2["ready_now"] == 1, plan2["ready_now"])
check("have flag set", b2["aadhaar"]["have"] is True and b2["aadhaar"]["unlocks"] == 0)
check("bank_passbook now unlocks Maternity Support",
      "Maternity Support" in b2["bank_passbook"]["unlock_examples"], b2["bank_passbook"])

plan3 = eligibility.plan_documents(have=["aadhaar", "bank_passbook", "nonsense"])
check("unknown have-key ignored", plan3["ready_now"] == 2, plan3["ready_now"])

plan4 = eligibility.plan_documents(category="farmer", age=70)
check("planner respects profile filters", plan4["total_schemes"] == 2, plan4["total_schemes"])  # Kisan (18-60) excluded by age 70

# ---------------------------------------------------------------- 6.6 events
print("\n6.6 life events")
r = eligibility.filter_schemes(event="new_baby")
check("new_baby finds Maternity Support only", [m["scheme_name"] for m in r["matches"]] == ["Maternity Support"], r["matches"])
ev_reason = [x for x in r["matches"][0]["reasons"] if x["field"] == "event"]
check("event reason present and matched", len(ev_reason) == 1 and ev_reason[0]["status"] == "matched" and ev_reason[0]["code"] == "event_match")
check("event reason note mentions label", "Had a baby" in ev_reason[0]["note"], ev_reason[0]["note"])
r = eligibility.filter_schemes(event="retiring")
check("retiring finds the pension scheme", [m["slug"] for m in r["matches"]] == ["aadhaar-only-pension"])
r = eligibility.filter_schemes(event="start_business")
check("start_business finds MUDRA", [m["slug"] for m in r["matches"]] == ["mudra-starter"])
r = eligibility.filter_schemes(event="start_business", age=70)
check("event + age filter combine", r["total_matched"] == 0)
r = eligibility.filter_schemes(event="not_an_event")
check("unknown event ignored (no event filter)", r["total_matched"] == 7)
r = eligibility.filter_schemes()
check("no event -> no event reason", all(x["field"] != "event" for m in r["matches"] for x in m["reasons"]))
check("name/tag hits outrank body-only hits",
      eligibility._event_score(df.iloc[1], "new_baby")[0] > eligibility._event_score(df.iloc[0], "new_baby")[0])
check("old four-argument call still works", eligibility.filter_schemes(age=30, income=100000, state="Kerala", category="student")["total_matched"] >= 1)

# ---------------------------------------------------------------- 6.7 verify
print("\n6.7 verify")
import verify  # noqa: E402
import json

elig_text = df[df.slug == "kisan-aadhaar"].iloc[0]["eligibility"]
good = [{"slug": "kisan-aadhaar", "verdict": "likely", "reason": "Age and income fit.",
         "quote": "Farmers aged 18 to 60 years with income not exceeding Rs 1,50,000."}]
GEMINI_REPLY["raise"] = None
GEMINI_REPLY["text"] = "```json\n" + json.dumps(good) + "\n```"
out = verify.verify_shortlist(["kisan-aadhaar"], age=40, income=100000)
v = out["verdicts"][0]
check("fenced JSON parsed, real quote kept", v["verdict"] == "likely" and v["quote"].startswith("Farmers aged"), v)
check("prompt carries the profile", "Age: 40" in GEMINI_REPLY["last_prompt"] and "Rs 100000" in GEMINI_REPLY["last_prompt"])
check("prompt carries the eligibility text", "18 to 60 years" in GEMINI_REPLY["last_prompt"])

fake = [{"slug": "kisan-aadhaar", "verdict": "not_eligible", "reason": "Too old.", "quote": "Applicants must be under 30."}]
GEMINI_REPLY["text"] = json.dumps(fake)
v = verify.verify_shortlist(["kisan-aadhaar"], age=70)["verdicts"][0]
check("invented quote -> downgraded to unclear", v["verdict"] == "unclear" and v["quote"] == "", v)

GEMINI_REPLY["text"] = "Sorry, I cannot do that."
v = verify.verify_shortlist(["kisan-aadhaar"], age=40)["verdicts"][0]
check("non-JSON reply -> unclear, no crash", v["verdict"] == "unclear", v)

GEMINI_REPLY["text"] = json.dumps([{"slug": "kisan-aadhaar", "verdict": "definitely", "reason": "x", "quote": "y"}])
v = verify.verify_shortlist(["kisan-aadhaar"], age=40)["verdicts"][0]
check("invalid verdict value -> unclear", v["verdict"] == "unclear")

GEMINI_REPLY["text"] = json.dumps([{"slug": "kisan-aadhaar", "verdict": "unclear", "reason": "Not stated.", "quote": ""}])
v = verify.verify_shortlist(["kisan-aadhaar", "kisan-aadhaar"], age=40)
check("duplicate slugs collapsed", v["checked"] == 1)

many = [r_[1] for r_ in ROWS] * 2
GEMINI_REPLY["text"] = "[]"
out = verify.verify_shortlist(many, age=40)
check("capped at MAX_SCHEMES", out["checked"] == verify.MAX_SCHEMES, out["checked"])

try:
    verify.verify_shortlist(["kisan-aadhaar"])
    check("empty profile rejected", False)
except verify.VerifyError:
    check("empty profile rejected", True)
try:
    verify.verify_shortlist(["no-such-slug"], age=40)
    check("unknown slugs rejected", False)
except verify.VerifyError:
    check("unknown slugs rejected", True)

# ---------------------------------------------------------------- API
print("\nAPI")
from fastapi.testclient import TestClient  # noqa: E402
import app as app_module  # noqa: E402
client = TestClient(app_module.app)

r = client.get("/eligibility/options").json()
check("/eligibility/options lists events", r["events"].get("new_baby") == "Had a baby / expecting")

r = client.post("/eligibility", json={"event": "new_baby"})
check("/eligibility with event", r.status_code == 200 and r.json()["total_matched"] == 1)
r = client.post("/eligibility", json={"event": "bogus"})
check("/eligibility bad event -> 400", r.status_code == 400)
r = client.post("/eligibility", json={"age": 40})
check("/eligibility old request shape still works", r.status_code == 200)

r = client.post("/documents/plan", json={"category": "farmer", "have": ["aadhaar"]})
check("/documents/plan ok", r.status_code == 200 and r.json()["total_schemes"] >= 1, r.text)
r = client.post("/documents/plan", json={"event": "bogus"})
check("/documents/plan bad event -> 400", r.status_code == 400)
r = client.post("/documents/plan", json={"have": ["x"] * 21})
check("/documents/plan too many 'have' -> 422", r.status_code == 422)

GEMINI_REPLY["raise"] = None
GEMINI_REPLY["text"] = json.dumps(good)
r = client.post("/eligibility/verify", json={"slugs": ["kisan-aadhaar"], "age": 40, "income": 100000})
check("/eligibility/verify ok", r.status_code == 200 and r.json()["verdicts"][0]["verdict"] == "likely", r.text)
r = client.post("/eligibility/verify", json={"slugs": ["kisan-aadhaar"]})
check("/eligibility/verify empty profile -> 400", r.status_code == 400)
r = client.post("/eligibility/verify", json={"slugs": ["a"] * 11, "age": 40})
check("/eligibility/verify >10 slugs -> 422", r.status_code == 422)
GEMINI_REPLY["raise"] = LLMError("quota", "limit")
r = client.post("/eligibility/verify", json={"slugs": ["kisan-aadhaar"], "age": 40})
check("/eligibility/verify quota -> 429", r.status_code == 429)
GEMINI_REPLY["raise"] = LLMError("unavailable", "down")
r = client.post("/eligibility/verify", json={"slugs": ["kisan-aadhaar"], "age": 40})
check("/eligibility/verify unreachable -> 503", r.status_code == 503)
GEMINI_REPLY["raise"] = RuntimeError("boom")
r = client.post("/eligibility/verify", json={"slugs": ["kisan-aadhaar"], "age": 40})
check("/eligibility/verify unexpected -> 500, no leak", r.status_code == 500 and "boom" not in r.text)


# ---------------------------------------------------------------- state names
print("\nstate name detection")
xs = eligibility._extract_states
check("'Jammu & Kashmir' (ampersand) detected", xs("The applicant should be a resident of Jammu & Kashmir.") == ["Jammu and Kashmir"], xs("resident of Jammu & Kashmir"))
check("'Jammu and Kashmir' still detected", xs("resident of Jammu and Kashmir") == ["Jammu and Kashmir"])
check("'Andaman & Nicobar Islands' detected", xs("Andaman & Nicobar Islands") == ["Andaman and Nicobar Islands"])
check("ampersand with odd spacing", xs("Jammu&Kashmir") == ["Jammu and Kashmir"])
check("old names map to current states", xs("a resident of Orissa") == ["Odisha"] and xs("Pondicherry") == ["Puducherry"])
check("two states named -> ambiguous, kept", xs("Kerala and Tamil Nadu") == [])
check("no state -> empty", xs("Applicants should be farmers.") == [])

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
