"""
test_api.py -- backend tests for SchemeSetu that need NO internet, FAISS,
embedding model or Gemini key.

How: the heavy libraries (langchain, google.generativeai) are replaced by tiny
stubs, and every file the app touches lives in a temporary folder, so your real
data/updated_data.csv is never read or modified.

Run (from the `files` folder, venv active):
    python test_api.py
Exit code is 0 only if every test passes.
"""

import io
import os
import sys
import tempfile
import threading
import types
from pathlib import Path

# ---------------------------------------------------------------- stubs ----
os.environ["GEMINI_API_KEY"] = "test-key"


def _stub(name, **attrs):
    mod = types.ModuleType(name)
    mod.__dict__.update(attrs)
    sys.modules[name] = mod
    return mod


class _FakeEmbeddings:
    def __init__(self, *a, **k):
        pass


class _FakeFAISS:
    @staticmethod
    def load_local(*a, **k):
        return object()


_stub("langchain_huggingface", HuggingFaceEmbeddings=_FakeEmbeddings)
_stub("langchain_community")
_stub("langchain_community.vectorstores", FAISS=_FakeFAISS)

_genai_behaviour = {"exc": None, "text": "ok", "raise_value_error": False, "responder": None}


class _FakeResponse:
    @property
    def text(self):
        if _genai_behaviour["raise_value_error"]:
            raise ValueError("blocked")
        return _genai_behaviour["text"]


_prompts = []


class _FakeModel:
    def __init__(self, name):
        self.name = name

    def generate_content(self, prompt):
        _prompts.append(prompt)
        if _genai_behaviour["exc"]:
            raise _genai_behaviour["exc"]
        responder = _genai_behaviour.get("responder")
        if responder:
            _genai_behaviour["text"] = responder(prompt)
        return _FakeResponse()


genai = _stub("google.generativeai", configure=lambda **k: None, GenerativeModel=_FakeModel)
_stub("google")
sys.modules["google"].generativeai = genai

# Fake `ingest` so Reindex works without langchain; behaviour is switchable.
_ingest_behaviour = {"fail": False, "delay": None}


def _fake_load_documents():
    if _ingest_behaviour["fail"]:
        raise RuntimeError("embedding model download failed")
    if _ingest_behaviour["delay"]:
        _ingest_behaviour["delay"].wait(5)
    return ["doc"] * 3


_stub(
    "ingest",
    load_documents=_fake_load_documents,
    split_documents=lambda docs: docs * 2,
    build_index=lambda chunks: None,
)

# ------------------------------------------------- temp data + app import ---
TMP = Path(tempfile.mkdtemp(prefix="schemesetu_test_"))
(TMP / "data").mkdir()

import pandas as pd  # noqa: E402

SEED = pd.DataFrame(
    [
        {
            "scheme_name": "Kisan Central Aid", "slug": "kisan-central-aid", "level": "Central",
            "schemeCategory": "Agriculture", "tags": "farmer",
            "eligibility": "Farmers aged 18 to 60 years with annual income not exceed Rs. 200000.",
            "details": "Support for farmers.", "benefits": "Rs 6000 per year.",
            "application": "Apply online.", "documents": "Aadhaar",
        },
        {
            "scheme_name": "Tamil Nadu Farmer Pension", "slug": "tn-farmer-pension", "level": "State",
            "schemeCategory": "Agriculture", "tags": "farmer",
            "eligibility": "Farmers of Tamil Nadu above 60 years.",
            "details": "Pension for farmers in Tamil Nadu.", "benefits": "Monthly pension.",
            "application": "Apply at the taluk office.", "documents": "Ration card",
        },
        {
            "scheme_name": "Kerala Student Grant", "slug": "kerala-student-grant", "level": "State",
            "schemeCategory": "Education", "tags": "student",
            "eligibility": "Students studying in Kerala colleges.",
            "details": "Grant for students in Kerala.", "benefits": "Fee waiver.",
            "application": "Apply via college.", "documents": "Marksheet",
        },
        {
            "scheme_name": "Open Women Scheme", "slug": "open-women-scheme", "level": "Central",
            "schemeCategory": "Women", "tags": "women",
            "eligibility": "Women who are residents of India.",
            "details": "General support.", "benefits": "Training.",
            "application": "Apply online.", "documents": "Aadhaar",
        },
    ]
)
SEED_PATH = TMP / "data" / "updated_data.csv"
SEED.to_csv(SEED_PATH, index=False, encoding="utf-8-sig")

import admin  # noqa: E402
import eligibility  # noqa: E402

admin.DATA_DIR = TMP / "data"
admin.CSV_PATH = SEED_PATH
eligibility.CSV_PATH = SEED_PATH

import rag_chat  # noqa: E402  (real module, stubbed libraries)

rag_chat.load_index = lambda: object()
import app as app_module  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

client = TestClient(app_module.app, raise_server_exceptions=False)

# --------------------------------------------------------------- harness ----
results = []


def check(test_id, description, condition, detail=""):
    results.append((test_id, description, bool(condition), detail))
    print(f"[{'PASS' if condition else 'FAIL'}] {test_id}: {description}" + (f"  -- {detail}" if (detail and not condition) else ""))


def reset_csv():
    SEED.to_csv(SEED_PATH, index=False, encoding="utf-8-sig")
    eligibility.load_dataframe(force_reload=True)


def names(resp):
    return {m["scheme_name"] for m in resp.json()["matches"]}


# ------------------------------------------------------------- general ------
r = client.get("/")
check("API-01", "Health check returns running status", r.status_code == 200 and "running" in r.json()["status"])

# ------------------------------------------------------------- /ask ---------
_seen = {}


def _fake_full(vs, q, history=None, language="en"):
    _seen.update(question=q, history=history, language=language)
    return {"answer": "Farmers get Rs 6000.", "sources": ["PM-KISAN (page N/A)"],
            "is_fallback": False, "english_question": "english: " + q}


app_module.answer_question_full = _fake_full
r = client.post("/ask", json={"question": "Who is eligible for PM-KISAN?", "history": []})
check("ASK-01", "Valid question returns answer + sources", r.status_code == 200 and r.json()["sources"] == ["PM-KISAN (page N/A)"])

r = client.post("/ask", json={"question": "   ", "history": []})
check("ASK-02", "Blank question is rejected with 400", r.status_code == 400, r.text)

r = client.post("/ask", json={"question": "x" * 2001, "history": []})
check("ASK-03", "Oversized question is rejected with 422", r.status_code == 422, r.text)


def _raise(exc):
    def f(*a, **k):
        raise exc
    return f


app_module.answer_question_full = _raise(rag_chat.LLMError("quota", "The AI service's usage limit was reached."))
r = client.post("/ask", json={"question": "hi", "history": []})
check("ASK-04", "Gemini quota error becomes HTTP 429 with readable message", r.status_code == 429 and "limit" in r.json()["detail"], r.text)

app_module.answer_question_full = _raise(rag_chat.LLMError("unavailable", "The AI service could not be reached."))
r = client.post("/ask", json={"question": "hi", "history": []})
check("ASK-05", "Gemini outage becomes HTTP 503", r.status_code == 503, r.text)

app_module.answer_question_full = _raise(KeyError("secret internal detail"))
r = client.post("/ask", json={"question": "hi", "history": []})
check("ASK-06", "Unexpected error becomes 500 without leaking internals", r.status_code == 500 and "secret" not in r.text, r.text)

# ------------------------------------------------- ask_gemini (real code) ----
_genai_behaviour.update(exc=None, text="  hello  ", raise_value_error=False)
check("LLM-01", "ask_gemini returns text on success", rag_chat.ask_gemini("p").strip() == "hello")

_genai_behaviour["exc"] = RuntimeError("429 You exceeded your current quota")
try:
    rag_chat.ask_gemini("p")
    kind = None
except rag_chat.LLMError as e:
    kind = e.kind
check("LLM-02", "429 / quota exception is classified as 'quota'", kind == "quota", str(kind))

_genai_behaviour["exc"] = ConnectionError("network down")
try:
    rag_chat.ask_gemini("p")
    kind = None
except rag_chat.LLMError as e:
    kind = e.kind
check("LLM-03", "Network failure is classified as 'unavailable'", kind == "unavailable", str(kind))

_genai_behaviour.update(exc=None, raise_value_error=True)
try:
    rag_chat.ask_gemini("p")
    kind = None
except rag_chat.LLMError as e:
    kind = e.kind
check("LLM-04", "Blocked/empty Gemini reply is classified as 'unavailable'", kind == "unavailable", str(kind))
_genai_behaviour.update(exc=None, raise_value_error=False, text="ok")

# --------------------------------------------------------- eligibility -------
reset_csv()
r = client.get("/eligibility/options")
check("ELIG-01", "Options endpoint lists states and 7 categories", r.status_code == 200 and "Tamil Nadu" in r.json()["states"] and len(r.json()["categories"]) == 7)

r = client.post("/eligibility", json={"state": "Tamil Nadu", "category": "farmer"})
check("ELIG-02", "Farmer in Tamil Nadu gets central + TN schemes, not Kerala", names(r) == {"Kisan Central Aid", "Tamil Nadu Farmer Pension"}, str(names(r)))

r = client.post("/eligibility", json={"state": "Kerala"})
n = names(r)
check("ELIG-03", "State filter excludes other states' State-level schemes", "Tamil Nadu Farmer Pension" not in n and "Kerala Student Grant" in n and "Kisan Central Aid" in n, str(n))

r = client.post("/eligibility", json={"age": 25, "category": "farmer"})
n = names(r)
check("ELIG-04", "Age 25 excluded from 'above 60' scheme, included in 18-60 scheme", "Kisan Central Aid" in n and "Tamil Nadu Farmer Pension" not in n, str(n))

r = client.post("/eligibility", json={"income": 500000, "category": "farmer"})
check("ELIG-05", "Income above a scheme's ceiling excludes it", "Kisan Central Aid" not in names(r), str(names(r)))

r = client.post("/eligibility", json={"age": 30, "income": 100000, "state": "Kerala", "category": "woman"})
check("ELIG-06", "Scheme with no stated constraints is kept (benefit of the doubt)", "Open Women Scheme" in names(r), str(names(r)))

r = client.post("/eligibility", json={})
j = r.json()
check("ELIG-07", "Empty profile returns every scheme", j["total_matched"] == 4 and j["returned"] == 4)

r = client.post("/eligibility", json={"age": 500})
check("ELIG-08", "Impossible age is rejected with 422", r.status_code == 422, r.text)

r = client.post("/eligibility", json={"category": "farmer"})
check("ELIG-09", "Match objects expose the 'category' key", r.status_code == 200 and "category" in r.json()["matches"][0] and "scheme_category" not in r.json()["matches"][0])

# ------------------------------------------------------------- admin routes ---
r = client.get("/admin/schemes")
check("ADM-01", "Admin routes are available in local development", r.status_code == 200)

# ------------------------------------------------------------- admin CRUD ---
reset_csv()
r = client.post("/admin/schemes", json={"scheme_name": "Test Setu Yojana", "eligibility": "Farmers in Tamil Nadu.", "schemeCategory": "Agriculture", "tags": "farmer"})
body = r.json()
check("ADM-05", "Create scheme auto-generates slug and defaults blank level to Central", r.status_code == 200 and body["slug"] == "test-setu-yojana" and body["level"] == "Central", r.text)

r = client.post("/admin/schemes", json={"scheme_name": "Test Setu Yojana"})
check("ADM-06", "Duplicate name gets a unique slug (-2)", r.json()["slug"] == "test-setu-yojana-2", r.text)

r = client.post("/admin/schemes", json={"details": "no name"})
check("ADM-07", "Create without scheme_name -> 422", r.status_code == 422)
r = client.post("/admin/schemes", json={"scheme_name": "   "})
check("ADM-08", "Create with whitespace-only name -> 400", r.status_code == 400, r.text)

r = client.put("/admin/schemes/test-setu-yojana", json={"benefits": "Rs 1000", "slug": "hacked"})
check("ADM-09", "Update changes fields but slug stays immutable", r.status_code == 200 and r.json()["benefits"] == "Rs 1000" and r.json()["slug"] == "test-setu-yojana", r.text)

r = client.get("/admin/schemes/test-setu-yojana")
check("ADM-10", "Get one scheme by slug", r.status_code == 200 and r.json()["scheme_name"] == "Test Setu Yojana")
r = client.get("/admin/schemes/does-not-exist")
check("ADM-11", "Unknown slug -> 404", r.status_code == 404)

r = client.get("/admin/schemes?search=kerala")
check("ADM-12", "Search filters the list", r.json()["total"] == 1, r.text)
r = client.get("/admin/schemes?page=-1")
check("ADM-13", "Invalid page number -> 400 (not a crash)", r.status_code == 400, str(r.status_code))

r = client.delete("/admin/schemes/test-setu-yojana-2")
check("ADM-14", "Delete removes the scheme", r.status_code == 200 and client.get("/admin/schemes/test-setu-yojana-2").status_code == 404)
r = client.delete("/admin/schemes/test-setu-yojana-2")
check("ADM-15", "Deleting twice -> 404", r.status_code == 404)

check("ADM-16", "Writes leave no .tmp file behind", not list((TMP / "data").glob("*.tmp")))

# ------------------------------------------------------------ CSV upload ----
reset_csv()
before = SEED_PATH.read_bytes()


def upload_csv(name, data):
    return client.post("/admin/upload/csv", files={"file": (name, io.BytesIO(data), "text/csv")})


r = upload_csv("notes.txt", b"scheme_name\nX")
check("UP-01", "Non-.csv filename -> 400", r.status_code == 400, r.text)
r = upload_csv("empty.csv", b"")
check("UP-02", "Empty CSV -> 400", r.status_code == 400, r.text)
r = upload_csv("bad.csv", b"title,body\nA,B\n")
check("UP-03", "CSV without scheme_name column -> 400", r.status_code == 400 and "scheme_name" in r.json()["detail"], r.text)
r = upload_csv("garbage.csv", b"\xff\xfe\x00\x01\x02 not utf8 \x80\x81")
check("UP-04", "Binary garbage CSV -> 400", r.status_code == 400, r.text)
r = upload_csv("norows.csv", b"scheme_name,slug\n,\n")
check("UP-05", "CSV with no usable rows -> 400", r.status_code == 400, r.text)
check("UP-06", "All rejected uploads left the existing CSV untouched", SEED_PATH.read_bytes() == before)

good = b"scheme_name,details\nNew Scheme A,Some details\nNew Scheme B,Other\nNew Scheme A,Dup name\n"
r = upload_csv("new.csv", good)
slugs = [s["slug"] for s in client.get("/admin/schemes").json()["schemes"]]
check("UP-07", "Valid CSV replaces data, missing columns filled, unique slugs generated", r.status_code == 200 and r.json()["rows"] == 3 and len(set(slugs)) == 3, f"{r.text} {slugs}")

# ------------------------------------------------------------ PDF upload ----
reset_csv()
r = client.post("/admin/upload/pdf", files={"file": ("fake.pdf", io.BytesIO(b"not a pdf"), "application/pdf")})
check("UP-08", "Fake PDF content -> 400", r.status_code == 400, r.text)
r = client.post("/admin/upload/pdf", files={"file": ("../../evil.pdf", io.BytesIO(b"%PDF-1.4 test"), "application/pdf")})
check("UP-09", "Valid PDF saved with folder parts stripped (no path traversal)", r.status_code == 200 and (TMP / "data" / "evil.pdf").exists() and r.json()["filename"] == "evil.pdf", r.text)

# --------------------------------------------------------------- reindex ----
reset_csv()
client.post("/admin/schemes", json={"scheme_name": "Reindex Probe Scheme", "level": "Central", "eligibility": "Open to all.", "tags": "farmer", "schemeCategory": "Agriculture"})
r = client.post("/eligibility", json={"category": "farmer"})
check("RIX-01", "New scheme is NOT visible in eligibility before Reindex (deliberate)", "Reindex Probe Scheme" not in names(r))
r = client.post("/admin/reindex")
check("RIX-02", "Reindex succeeds and reports counts", r.status_code == 200 and r.json()["documents"] == 3, r.text)
r = client.post("/eligibility", json={"category": "farmer"})
check("RIX-03", "After Reindex the new scheme appears in eligibility results", "Reindex Probe Scheme" in names(r), str(names(r)))

_ingest_behaviour["fail"] = True
r = client.post("/admin/reindex")
check("RIX-04", "Reindex failure -> 500 with explanation, server stays up", r.status_code == 500 and "Reindex failed" in r.json()["detail"], r.text)
check("RIX-05", "Chat/eligibility still work after a failed Reindex", client.post("/eligibility", json={}).status_code == 200)
_ingest_behaviour["fail"] = False

gate = threading.Event()
_ingest_behaviour["delay"] = gate
first = {}
t = threading.Thread(target=lambda: first.update(r=client.post("/admin/reindex")))
t.start()
import time  # noqa: E402
time.sleep(0.5)
r2 = client.post("/admin/reindex")
gate.set()
t.join()
_ingest_behaviour["delay"] = None
check("RIX-06", "A second Reindex while one is running -> 409", r2.status_code == 409, r2.text)
check("RIX-07", "The first Reindex still completes", first["r"].status_code == 200, first["r"].text)

r = client.post("/admin/reindex")
check("RIX-08", "Reindex route is available in local development", r.status_code == 200)


# ===================================================== regional languages ====
from types import SimpleNamespace  # noqa: E402

PMK_DOC = SimpleNamespace(
    page_content="Scheme Name: PM-KISAN\n\nEligibility: Small farmers.",
    metadata={"source": "PM-KISAN", "scheme_name": "PM-KISAN", "slug": "pm-kisan", "page": "N/A"},
)


class FakeStore:
    """Mimics the bits of a LangChain FAISS store that rag_chat touches."""

    def __init__(self, distance=0.5):
        self.distance = distance
        self.docstore = SimpleNamespace(_dict={"0": PMK_DOC})
        self.queries = []

    def similarity_search_with_score(self, question, **opts):
        self.queries.append((question, opts))
        return [(PMK_DOC, self.distance)]


def responder_factory(answer="Farmers get Rs 6000 per year.", translation="Who is eligible for PM-KISAN?"):
    def respond(prompt):
        if prompt.startswith("Translate this question"):
            return translation
        return answer
    return respond


def run(question, language, store=None, history=None, answer="Farmers get Rs 6000 per year.", translation="Who is eligible for PM-KISAN?"):
    _prompts.clear()
    _genai_behaviour.update(exc=None, raise_value_error=False,
                            responder=responder_factory(answer, translation))
    store = store or FakeStore()
    result = rag_chat.answer_question_full(store, question, history=history, language=language)
    return result, store, list(_prompts)


TA_Q = "PM-KISAN க்கு யார் தகுதி?"

# ---- API layer
app_module.answer_question_full = _fake_full
r = client.post("/ask", json={"question": TA_Q, "history": [], "language": "ta"})
j = r.json()
check("LANG-01", "/ask forwards language and returns english_question + is_fallback",
      r.status_code == 200 and _seen["language"] == "ta" and j["english_question"].startswith("english:") and j["is_fallback"] is False, r.text)

r = client.post("/ask", json={"question": "hi", "history": [], "language": "xx"})
check("LANG-02", "Unsupported language on /ask -> 400", r.status_code == 400, r.text)

r = client.post("/ask", json={"question": "hi", "history": []})
check("LANG-03", "Language defaults to English when omitted", r.status_code == 200 and _seen["language"] == "en")

r = client.get("/languages")
check("LANG-04", "/languages lists the 10 supported languages", r.status_code == 200 and set(r.json()["languages"]) == {"en", "hi", "ta", "te", "kn", "ml", "mr", "bn", "gu", "pa"}, r.text)

app_module.translate_text = lambda text, lang: f"[{lang}] {text}"
r = client.post("/translate", json={"text": "Farmers aged 18-60.", "language": "hi"})
check("LANG-05", "/translate returns a translation", r.status_code == 200 and r.json()["translation"] == "[hi] Farmers aged 18-60.", r.text)
check("LANG-06", "/translate rejects unsupported language (400)", client.post("/translate", json={"text": "x", "language": "zz"}).status_code == 400)
check("LANG-07", "/translate rejects blank text (400)", client.post("/translate", json={"text": "  ", "language": "hi"}).status_code == 400)
check("LANG-08", "/translate rejects oversized text (422)", client.post("/translate", json={"text": "x" * 3001, "language": "hi"}).status_code == 422)
app_module.translate_text = _raise(rag_chat.LLMError("quota", "limit"))
check("LANG-09", "/translate maps quota error to 429", client.post("/translate", json={"text": "x", "language": "hi"}).status_code == 429)
app_module.translate_text = _raise(RuntimeError("boom"))
check("LANG-10", "/translate hides unexpected errors behind a 500", client.post("/translate", json={"text": "x", "language": "hi"}).status_code == 500)

check("LANG-11", "Every language has a localized fallback message; non-English ones differ from English",
      set(rag_chat.FALLBACK_MESSAGES) == set(rag_chat.LANGUAGES)
      and all(rag_chat.FALLBACK_MESSAGES[c] != rag_chat.FALLBACK_EN for c in rag_chat.LANGUAGES if c != "en"))

# ---- pipeline (real rag_chat code, fake index, fake Gemini)
result, store, prompts = run(TA_Q, "ta")
check("PIPE-01", "Tamil question is translated to English and retrieval uses the English text",
      store.queries[0][0] == "Who is eligible for PM-KISAN?" and result["english_question"] == "Who is eligible for PM-KISAN?" and prompts[0].startswith("Translate this question"),
      str(store.queries))
check("PIPE-02", "Named-scheme filter still works on the translated question", store.queries[0][1].get("filter") == {"source": "PM-KISAN"}, str(store.queries[0][1]))
check("PIPE-03", "Answer prompt asks for Tamil and carries the NO_INFO rule",
      "ENTIRE answer in Tamil" in prompts[-1] and rag_chat.NO_INFO_TOKEN in prompts[-1] and "Who is eligible for PM-KISAN?" in prompts[-1])

result, store, prompts = run("Who is eligible for PM-KISAN?", "ta")
check("PIPE-04", "Plain-English question in Tamil mode skips the translate call (saves quota)", len(prompts) == 1 and not prompts[0].startswith("Translate this question"), str(len(prompts)))

result, store, prompts = run("Who is eligible for PM-KISAN?", "en")
check("PIPE-05", "English mode makes exactly one Gemini call and keeps the original English prompt",
      len(prompts) == 1 and "ENTIRE answer in" not in prompts[0] and "I could not find this information in the available scheme documents." in prompts[0])

result, store, prompts = run(TA_Q, "ta", answer=rag_chat.NO_INFO_TOKEN)
check("PIPE-06", "Model says NO_INFO_FOUND -> localized Tamil fallback, is_fallback, no sources",
      result["answer"] == rag_chat.FALLBACK_MESSAGES["ta"] and result["is_fallback"] and result["sources"] == [])

result, store, prompts = run("मौसम कैसा है", "hi", store=FakeStore(distance=3.0), translation="How is the weather")
check("PIPE-07", "Low retrieval confidence -> localized Hindi fallback WITHOUT calling the answer model",
      result["answer"] == rag_chat.FALLBACK_MESSAGES["hi"] and result["is_fallback"] and len(prompts) == 1, str(len(prompts)))

hist = [{"question": "Who is eligible for PM-KISAN?", "answer": "பதில்"}]
result, store, prompts = run("அதற்கு என்ன ஆவணங்கள் தேவை?", "ta", history=hist, translation="What documents do I need for that?")
check("PIPE-08", "Tamil follow-up resolves to the scheme from English history",
      store.queries[0][1].get("filter") == {"source": "PM-KISAN"} and store.queries[0][0].startswith("PM-KISAN:"), str(store.queries))

result, store, prompts = run("Who is eligible?", "en", answer="I could not find this information in the available scheme documents.")
check("PIPE-09", "English answer containing the refusal phrase is flagged is_fallback", result["is_fallback"] is True)

result, store, prompts = run("Who is eligible for PM-KISAN?", "en")
check("PIPE-10", "Normal answer is not flagged as fallback and lists its source",
      result["is_fallback"] is False and result["sources"] == ["PM-KISAN (page N/A)"])

result, store, prompts = run("kisan ke liye kaun si yojana hai", "hi", translation="Which scheme is there for farmers?")
check("PIPE-14", "Romanized Hindi (what a mic can return) IS translated, not mistaken for English",
      prompts[0].startswith("Translate this question") and store.queries[0][0] == "Which scheme is there for farmers?", str(store.queries))
result, store, prompts = run("PM-KISAN", "ta", translation="PM-KISAN")
check("PIPE-15", "A bare scheme name in a non-English chat gets one safe translate pass", prompts[0].startswith("Translate this question"))
result, store, prompts = run("What schemes are there for farmers?", "ta")
check("PIPE-16", "Clearly English question in a non-English chat still skips translation", len(prompts) == 1)

_prompts.clear()
_genai_behaviour["responder"] = lambda p: "TRANSLATED"
check("PIPE-11", "translate_text('en') returns text unchanged without calling Gemini",
      rag_chat.translate_text("hello", "en") == "hello" and not _prompts)
check("PIPE-12", "translate_text keeps numbers/names instruction and returns model output",
      rag_chat.translate_text("Farmers get Rs 6000", "hi") == "TRANSLATED" and "Hindi" in _prompts[-1] and "rupee amounts" in _prompts[-1])

_genai_behaviour["responder"] = None
_genai_behaviour["exc"] = RuntimeError("429 quota")
try:
    rag_chat.answer_question_full(FakeStore(), TA_Q, language="ta")
    kind = None
except rag_chat.LLMError as e:
    kind = e.kind
check("PIPE-13", "Quota error during the translate step surfaces as LLMError('quota')", kind == "quota", str(kind))
_genai_behaviour.update(exc=None, text="ok")


# ============================================ explainable eligibility (6.3) ===
def reasons_of(resp, scheme):
    for m in resp.json()["matches"]:
        if m["scheme_name"] == scheme:
            return {r["field"]: r for r in m["reasons"]}
    return None


reset_csv()
r = client.post("/eligibility", json={"age": 25, "income": 100000, "state": "Tamil Nadu", "category": "farmer"})
kisan = reasons_of(r, "Kisan Central Aid")
check("WHY-01", "Every match carries exactly four reasons: age, income, state, category",
      r.status_code == 200 and all([x["field"] for x in m["reasons"]] == ["age", "income", "state", "category"] for m in r.json()["matches"]))
check("WHY-02", "Age inside a stated range -> matched/age_range with the numbers",
      kisan["age"]["status"] == "matched" and kisan["age"]["code"] == "age_range" and kisan["age"]["params"] == {"age": 25, "min": 18, "max": 60}, str(kisan["age"]))
check("WHY-03", "Income under a stated ceiling -> matched/income_ceiling",
      kisan["income"]["status"] == "matched" and kisan["income"]["params"] == {"income": 100000, "ceiling": 200000}, str(kisan["income"]))
check("WHY-04", "Central scheme -> state matched as 'applies across India'",
      kisan["state"]["code"] == "state_central" and kisan["state"]["status"] == "matched")
check("WHY-05", "Category match reports the keyword that was found in the text",
      kisan["category"]["status"] == "matched" and kisan["category"]["params"]["category"] == "farmer" and kisan["category"]["params"]["keyword"], str(kisan["category"]))

r = client.post("/eligibility", json={"age": 65, "income": 100000, "state": "Tamil Nadu", "category": "farmer"})
pension = reasons_of(r, "Tamil Nadu Farmer Pension")
check("WHY-06", "Open-ended minimum age ('above 60') -> matched/age_min",
      pension["age"]["code"] == "age_min" and pension["age"]["params"] == {"age": 65, "min": 60}, str(pension["age"]))
check("WHY-07", "No income limit in the text -> 'unverified', never silently 'matched'",
      pension["income"]["status"] == "unverified" and pension["income"]["code"] == "income_unverified")
check("WHY-08", "State-level scheme naming the user's state -> matched/state_match with the state",
      pension["state"]["code"] == "state_match" and pension["state"]["params"] == {"state": "Tamil Nadu"})

r = client.post("/eligibility", json={"age": 30, "income": 100000, "state": "Kerala", "category": "woman"})
open_w = reasons_of(r, "Open Women Scheme")
check("WHY-09", "Scheme with no age/income limit -> both flagged 'unverified' (the benefit-of-the-doubt cases)",
      open_w["age"]["status"] == "unverified" and open_w["income"]["status"] == "unverified", str(open_w))

r = client.post("/eligibility", json={})
check("WHY-10", "Empty profile -> every reason is 'na' (nothing was applied)",
      all(x["status"] == "na" for m in r.json()["matches"] for x in m["reasons"]))

r = client.post("/eligibility", json={"age": 25, "income": 100000, "state": "Tamil Nadu", "category": "farmer"})
check("WHY-11", "Every reason has an English note and a known status",
      all(x["note"] and x["status"] in ("matched", "unverified", "na") for m in r.json()["matches"] for x in m["reasons"]))
check("WHY-12", "English note contains the real numbers (Indian digit grouping for rupees)",
      kisan["income"]["note"] == "Income \u20b91,00,000 is within the limit of \u20b92,00,000" and "25" in kisan["age"]["note"], kisan["income"]["note"])

# the explanation must agree with the filter: nothing included can have a failed check
import itertools  # noqa: E402
profiles = [dict(age=a, income=i, state=s_, category=c) for a, i, s_, c in itertools.product([None, 25, 70], [None, 100000, 900000], [None, "Tamil Nadu", "Kerala"], [None, "farmer", "woman", "student"])]
bad = []
for prof in profiles:
    j = client.post("/eligibility", json=prof).json()
    for m in j["matches"]:
        if len(m["reasons"]) != 4:
            bad.append((prof, m["scheme_name"]))
check("WHY-13", f"Filter and explanation agree on all {len(profiles)} profile combinations (every match explainable)", not bad, str(bad[:2]))

import eligibility as _elig  # noqa: E402
check("WHY-14", "Indian rupee grouping helper", [_elig._inr(n) for n in (999, 1000, 150000, 1500000)] == ["999", "1,000", "1,50,000", "15,00,000"])
check("WHY-15", "Every reason code has an English template", all(c in _elig._NOTES for c in ("age_na","age_unverified","age_range","age_min","age_max","income_na","income_unverified","income_ceiling","state_na","state_central","state_match","state_unverified","category_na","category_match")))

# ---------------------------------------------------------------- summary ---
failed = [x for x in results if not x[2]]
print(f"\n{len(results) - len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)