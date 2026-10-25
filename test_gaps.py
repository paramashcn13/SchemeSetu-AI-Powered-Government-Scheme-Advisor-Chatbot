"""
test_gaps.py -- tests for 6.4 (data-gap log). No internet, FAISS or Gemini key
needed; rag_chat is stubbed and the log is written to a temp file.

Run from the folder that holds app.py:   python test_gaps.py
"""
import json
import os
import sys
import tempfile
import types
from pathlib import Path

import pandas as pd

TMP = Path(tempfile.mkdtemp())
os.environ["GAP_LOG_PATH"] = str(TMP / "gaps.jsonl")

class LLMError(Exception):
    def __init__(self, kind, message):
        super().__init__(message)
        self.kind = kind

def fake_answer(vectorstore, question, history=None, language="en"):
    if "tailor" in question.lower() or "darzi" in question.lower():
        return {"answer": "not found", "sources": [], "is_fallback": True,
                "english_question": "scheme for tailors", "top_confidence": 0.31, "named_scheme": None}
    if "pm-kisan" in question.lower():
        return {"answer": "x", "sources": ["PM-KISAN (page 1)"], "is_fallback": False,
                "english_question": question, "top_confidence": 0.8, "named_scheme": "PM-KISAN"}
    if "that scheme" in question.lower():
        return {"answer": "not found", "sources": [], "is_fallback": True,
                "english_question": question, "top_confidence": 0.2, "named_scheme": "PM-KISAN"}
    if "boom" in question.lower():
        raise LLMError("quota", "limit")
    return {"answer": "fine", "sources": [], "is_fallback": False, "english_question": question}

rag = types.ModuleType("rag_chat")
rag.LANGUAGES = {"en": "English", "hi": "Hindi"}
rag.LLMError = LLMError
rag.ask_gemini = lambda p: "[]"
rag.answer_question_full = fake_answer
rag.load_index = lambda: object()
rag.normalise_language = lambda l: l if l in rag.LANGUAGES else None
rag.translate_text = lambda t, l: t
sys.modules["rag_chat"] = rag

import eligibility  # noqa: E402
csv = TMP / "data.csv"
pd.DataFrame([("A", "a", "Central", "X", "", "Farmers.", "", "", "Aadhaar", "")],
             columns=["scheme_name", "slug", "level", "schemeCategory", "tags", "eligibility",
                      "details", "application", "documents", "benefits"]).to_csv(csv, index=False)
eligibility.CSV_PATH = csv

import gaplog  # noqa: E402

passed = failed = 0
def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}  {detail}")

LOG = Path(os.environ["GAP_LOG_PATH"])

print("\ngaplog unit")
check("no log yet -> empty summary", gaplog.summarise() == {"total_entries": 0, "unique_questions": 0, "gaps": []})
check("normalise ignores case/punctuation/spacing",
      gaplog.normalise_question("  Scheme for  TAILORS?! ") == gaplog.normalise_question("scheme for tailors"))
check("normalise keeps non-Latin letters", gaplog.normalise_question("दर्जी के लिए योजना?") == "दर्जी के लिए योजना")
check("blank question not logged", gaplog.log_gap("   ") is False and not LOG.exists())
check("log_gap writes", gaplog.log_gap("Scheme for tailors?", "scheme for tailors", "en", 0.3123, None) and LOG.exists())
gaplog.log_gap("scheme for tailors", "scheme for tailors", "en", 0.41, "Some Scheme")
gaplog.log_gap("दर्जी के लिए योजना", "Scheme for tailors!", "hi", 0.25, "Some Scheme")
gaplog.log_gap("unrelated thing", "unrelated thing", "en", None, None)
with open(LOG, "a", encoding="utf-8") as f:
    f.write("this is not json\n\n{\"no_question\": 1}\n")
gaplog.log_gap("x" * 900, "", "en")
sm = gaplog.summarise()
check("malformed lines skipped, rest counted", sm["total_entries"] == 5, sm["total_entries"])
top = sm["gaps"][0]
check("repeats grouped across punctuation + language", top["count"] == 3 and top["question"].lower().startswith("scheme for tailors"), top)
check("languages collected", top["languages"] == ["en", "hi"], top["languages"])
check("best confidence is the max", top["best_confidence"] == 0.41, top["best_confidence"])
check("most common named scheme", top["named_scheme"] == "Some Scheme")
check("original wording of latest entry kept", top["original_question"] == "दर्जी के लिए योजना")
check("question without confidence handled", [g for g in sm["gaps"] if g["question"] == "unrelated thing"][0]["best_confidence"] is None)
check("long question truncated", any(len(g["original_question"]) == 500 for g in sm["gaps"]))
check("limit respected", len(gaplog.summarise(limit=1)["gaps"]) == 1)
check("sorted most-asked first", [g["count"] for g in sm["gaps"]] == sorted([g["count"] for g in sm["gaps"]], reverse=True))
os.environ["GAP_LOG_PATH"] = str(TMP)          # a directory: opening it for append fails
unwritable_ok = gaplog.log_gap("q") is False
os.environ["GAP_LOG_PATH"] = str(LOG)
check("unwritable path does not raise", unwritable_ok)

print("\nAPI")
LOG.unlink()
from fastapi.testclient import TestClient  # noqa: E402
import app as app_module  # noqa: E402
client = TestClient(app_module.app)

r = client.post("/ask", json={"question": "Is there a scheme for tailors?"})
check("fallback /ask still answers normally", r.status_code == 200 and r.json()["is_fallback"] is True)
check("extra keys not leaked in response", "top_confidence" not in r.json() and "named_scheme" not in r.json())
check("fallback was logged", LOG.exists() and len(LOG.read_text(encoding="utf-8").splitlines()) == 1)
entry = json.loads(LOG.read_text(encoding="utf-8").splitlines()[0])
check("log entry has confidence + translated question", entry["top_confidence"] == 0.31 and entry["english_question"] == "scheme for tailors", entry)

client.post("/ask", json={"question": "Tell me about PM-KISAN"})
client.post("/ask", json={"question": "hello"})
check("answered questions are NOT logged", len(LOG.read_text(encoding="utf-8").splitlines()) == 1)

client.post("/ask", json={"question": "what about that scheme?"})
last = json.loads(LOG.read_text(encoding="utf-8").splitlines()[-1])
check("named scheme recorded for follow-up fallbacks", last["named_scheme"] == "PM-KISAN", last)

r = client.post("/ask", json={"question": "boom"})
check("LLM error -> 429 and not logged", r.status_code == 429 and len(LOG.read_text(encoding="utf-8").splitlines()) == 2)
r = client.post("/ask", json={"question": "tailor", "language": "xx"})
check("bad language -> 400 and not logged", r.status_code == 400 and len(LOG.read_text(encoding="utf-8").splitlines()) == 2)

os.environ["GAP_LOG_PATH"] = str(TMP)          # break the log on purpose
r = client.post("/ask", json={"question": "darzi yojana"})
os.environ["GAP_LOG_PATH"] = str(LOG)
check("log failure never breaks /ask", r.status_code == 200 and r.json()["is_fallback"] is True, r.text)

r = client.get("/admin/gaps")
body = r.json()
check("/admin/gaps ok", r.status_code == 200 and body["total_entries"] == 2 and body["unique_questions"] == 2, body)
r = client.get("/admin/gaps?limit=1")
check("/admin/gaps limit", len(r.json()["gaps"]) == 1)
r = client.get("/admin/gaps?limit=0")
check("/admin/gaps limit clamped, not an error", r.status_code == 200 and len(r.json()["gaps"]) == 1)

print(f"\n{passed} passed, {failed} failed")
sys.exit(1 if failed else 0)
