import threading
import os
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

load_dotenv()

from rag_chat import (
    LANGUAGES,
    LLMError,
    answer_question_full,
    load_index,
    normalise_language,
    translate_text,
    translate_texts,
)
import eligibility
import admin
import verify
import gaplog

app = FastAPI(title="SchemeSetu API")

app.add_middleware(
    CORSMiddleware,
    # Only the websites listed in ALLOWED_ORIGINS (.env) may call this API from a browser.
    allow_origins=[origin.strip() for origin in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",") if origin.strip()],
    allow_methods=["*"],
    allow_headers=["Content-Type"],
)
 

print("Loading FAISS index...")
vectorstore = load_index()
print("Index loaded. API ready.")

print("Loading eligibility dataframe...")
eligibility.load_dataframe()
print("Eligibility filter ready.")
 
 
class HistoryTurn(BaseModel):
    question: str
    answer: str


class AskRequest(BaseModel):
    question: str = Field(max_length=2000)
    history: list[HistoryTurn] = Field(default=[], max_length=20)
    language: str = "en"  # one of rag_chat.LANGUAGES
 
 
class AskResponse(BaseModel):
    answer: str
    sources: list[str]
    is_fallback: bool = False
    # The question as the retrieval step saw it. The frontend stores THIS in
    # history so follow-ups still resolve scheme names in non-English chats.
    english_question: str = ""


class TranslateRequest(BaseModel):
    text: str = Field(max_length=3000)
    language: str
    source_language: str = "en"


class TranslateResponse(BaseModel):
    translation: str


class BatchTranslateRequest(BaseModel):
    texts: list[str] = Field(max_length=80)
    language: str
    source_language: str = "en"


class BatchTranslateResponse(BaseModel):
    translations: list[str]


class EligibilityRequest(BaseModel):
    age: int | None = Field(default=None, ge=0, le=120)
    income: int | None = Field(default=None, ge=0)
    state: str | None = None
    category: str | None = None
    event: str | None = None      # a key from eligibility.LIFE_EVENTS (6.6)


class DocumentPlanRequest(EligibilityRequest):
    have: list[str] = Field(default=[], max_length=20)   # document keys the user already holds


class SchemeDocumentsRequest(BaseModel):
    names: list[str] = Field(max_length=10)       # scheme names/slugs, e.g. an answer's sources
    have: list[str] = Field(default=[], max_length=20)


class SchemesInfoRequest(BaseModel):
    names: list[str] = Field(max_length=10)


class SchemeLink(BaseModel):
    name: str
    slug: str = ""
    url: str | None = None
    level: str = ""


class SchemesInfoResponse(BaseModel):
    data_updated: str | None = None
    schemes: dict[str, SchemeLink] = {}


class DocumentInfo(BaseModel):
    key: str
    label: str
    needed_by: int
    unlocks: int
    unlock_examples: list[str] = []
    have: bool = False


class DocumentPlanResponse(BaseModel):
    total_schemes: int
    ready_now: int
    docs_unknown: int
    documents: list[DocumentInfo]


class VerifyRequest(BaseModel):
    slugs: list[str] = Field(max_length=10)
    age: int | None = Field(default=None, ge=0, le=120)
    income: int | None = Field(default=None, ge=0)
    state: str | None = None
    category: str | None = None


class SchemeVerdict(BaseModel):
    slug: str
    scheme_name: str
    verdict: Literal["likely", "unclear", "not_eligible"]
    reason: str = ""
    quote: str = ""


class VerifyResponse(BaseModel):
    checked: int
    verdicts: list[SchemeVerdict]


class EligibilityReason(BaseModel):
    field: str                                  # age | income | state | category
    status: Literal["matched", "unverified", "na"]
    code: str                                   # stable key the frontend translates
    params: dict[str, str | int] = {}           # values for the sentence template
    note: str = ""                              # same sentence in English


class EligibilityMatch(BaseModel):
    scheme_name: str
    slug: str
    level: str
    state: str = ""
    category: str
    eligibility_snippet: str
    benefits_snippet: str
    reasons: list[EligibilityReason] = []
    apply_url: str | None = None
    documents_needed: list[dict[str, str]] = []
    documents_note: str = ""


class EligibilityResponse(BaseModel):
    total_matched: int
    returned: int
    matches: list[EligibilityMatch]


class EligibilityOptions(BaseModel):
    states: list[str]
    categories: dict[str, str]
    events: dict[str, str] = {}
 
 
@app.get("/")
def root():
    return {"status": "SchemeSetu API is running", "docs": "/docs"}
 
 
@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Please type a question.")
    language = normalise_language(request.language)
    if language is None:
        raise HTTPException(status_code=400, detail=f"Unsupported language '{request.language}'.")
    history = [turn.model_dump() for turn in request.history]
    try:
        result = answer_question_full(
            vectorstore, request.question, history=history, language=language
        )
    except LLMError as e:
        # 429 = our AI provider's quota; 503 = it is unreachable / returned nothing.
        status = 429 if e.kind == "quota" else 503
        raise HTTPException(status_code=status, detail=str(e))
    except Exception as e:  # keep the server alive and give the UI something readable
        print(f"[error] /ask failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Something went wrong while answering. Please try again.")
    if result.get("is_fallback"):
        # 6.4: remember what the data could not answer. Never fails /ask.
        gaplog.log_gap(
            request.question,
            english_question=result.get("english_question", ""),
            language=language,
            top_confidence=result.get("top_confidence"),
            named_scheme=result.get("named_scheme"),
        )
    return AskResponse(**result)


@app.get("/languages")
def languages():
    """Language codes the backend can answer in."""
    return {"languages": LANGUAGES}


@app.post("/translate", response_model=TranslateResponse)
def translate(request: TranslateRequest):
    """Translate one message or text snippet into the selected language."""
    language = normalise_language(request.language)
    if language is None:
        raise HTTPException(status_code=400, detail=f"Unsupported language '{request.language}'.")
    source_language = normalise_language(request.source_language)
    if source_language is None:
        raise HTTPException(status_code=400, detail=f"Unsupported source language '{request.source_language}'.")
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Nothing to translate.")
    try:
        return TranslateResponse(translation=translate_text(request.text, language, source_language))
    except LLMError as e:
        raise HTTPException(status_code=429 if e.kind == "quota" else 503, detail=str(e))
    except Exception as e:
        print(f"[error] /translate failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Translation failed. Please try again.")


@app.post("/translate/batch", response_model=BatchTranslateResponse)
def translate_batch(request: BatchTranslateRequest):
    language = normalise_language(request.language)
    source_language = normalise_language(request.source_language)
    if language is None or source_language is None:
        raise HTTPException(status_code=400, detail="Unsupported language.")
    if any(len(text) > 3000 for text in request.texts):
        raise HTTPException(status_code=400, detail="Each text must be at most 3000 characters.")
    try:
        return BatchTranslateResponse(translations=translate_texts(request.texts, language, source_language))
    except LLMError as e:
        raise HTTPException(status_code=429 if e.kind == "quota" else 503, detail=str(e))
    except Exception as e:
        print(f"[error] /translate/batch failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Translation failed. Please try again.")


@app.get("/eligibility/options", response_model=EligibilityOptions)
def eligibility_options():
    """States and categories the frontend can offer in its filter form,
    read straight from eligibility.py so the two never drift apart."""
    return EligibilityOptions(
        states=eligibility.STATES,
        categories=eligibility.CATEGORY_LABELS,
        events=eligibility.EVENT_LABELS,
    )


def _check_event(event):
    if event is not None and event not in eligibility.LIFE_EVENTS:
        raise HTTPException(status_code=400, detail=f"Unknown life event '{event}'.")


@app.post("/eligibility", response_model=EligibilityResponse)
def eligibility_filter(request: EligibilityRequest):
    _check_event(request.event)
    result = eligibility.filter_schemes(
        age=request.age,
        income=request.income,
        state=request.state,
        category=request.category,
        event=request.event,
    )
    return EligibilityResponse(**result)


@app.post("/documents/plan", response_model=DocumentPlanResponse)
def documents_plan(request: DocumentPlanRequest):
    """6.5 Document readiness planner. Same profile/event as /eligibility, plus
    the documents the user already has. Zero LLM calls."""
    _check_event(request.event)
    result = eligibility.plan_documents(
        age=request.age,
        income=request.income,
        state=request.state,
        category=request.category,
        event=request.event,
        have=request.have,
    )
    return DocumentPlanResponse(**result)


@app.post("/schemes/info", response_model=SchemesInfoResponse)
def schemes_info(request: SchemesInfoRequest):
    """Official-page links + data freshness date for an answer's sources."""
    return SchemesInfoResponse(
        data_updated=eligibility.data_updated(),
        schemes=eligibility.scheme_links(request.names),
    )


@app.post("/documents/for-schemes", response_model=DocumentPlanResponse)
def documents_for_schemes(request: SchemeDocumentsRequest):
    """Documents needed by specific schemes (e.g. the sources of a chat answer),
    so the planner is available under every answer. Zero LLM calls."""
    result = eligibility.plan_documents_for_names(request.names, have=request.have)
    return DocumentPlanResponse(**result)


@app.post("/eligibility/verify", response_model=VerifyResponse)
def eligibility_verify(request: VerifyRequest):
    """6.7 LLM-verified shortlist. ONE Gemini call for up to 5 schemes; the UI
    only calls this when the user clicks the button."""
    try:
        result = verify.verify_shortlist(
            request.slugs,
            age=request.age,
            income=request.income,
            state=request.state,
            category=request.category,
        )
    except verify.VerifyError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LLMError as e:
        raise HTTPException(status_code=429 if e.kind == "quota" else 503, detail=str(e))
    except Exception as e:
        print(f"[error] /eligibility/verify failed: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail="Verification failed. Please try again.")
    return VerifyResponse(**result)


# =============================================================================
# Admin dashboard (Feature 4)
# =============================================================================

class SchemeCreate(BaseModel):
    scheme_name: str
    slug: str | None = None
    details: str = ""
    benefits: str = ""
    eligibility: str = ""
    application: str = ""
    documents: str = ""
    level: str = ""
    schemeCategory: str = ""
    tags: str = ""


class SchemeUpdate(BaseModel):
    scheme_name: str | None = None
    details: str | None = None
    benefits: str | None = None
    eligibility: str | None = None
    application: str | None = None
    documents: str | None = None
    level: str | None = None
    schemeCategory: str | None = None
    tags: str | None = None


@app.get("/admin/gaps")
def admin_gaps(limit: int = 100):
    """6.4: questions the assistant could not answer, grouped and counted."""
    return gaplog.summarise(limit=min(max(limit, 1), 500))


@app.get("/admin/schemes")
def admin_list_schemes(search: str | None = None, page: int = 1, page_size: int = 25):
    try:
        return admin.list_schemes(search=search, page=page, page_size=page_size)
    except admin.AdminError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/admin/schemes/{slug}")
def admin_get_scheme(slug: str):
    try:
        return admin.get_scheme(slug)
    except admin.AdminError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/admin/schemes")
def admin_create_scheme(request: SchemeCreate):
    try:
        return admin.create_scheme(request.model_dump())
    except admin.AdminError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.put("/admin/schemes/{slug}")
def admin_update_scheme(slug: str, request: SchemeUpdate):
    try:
        return admin.update_scheme(slug, request.model_dump(exclude_unset=True))
    except admin.AdminError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.delete("/admin/schemes/{slug}")
def admin_delete_scheme(slug: str):
    try:
        return admin.delete_scheme(slug)
    except admin.AdminError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/admin/upload/csv")
async def admin_upload_csv(file: UploadFile = File(...)):
    try:
        content = await file.read()
        return admin.save_uploaded_csv(file.filename, content)
    except admin.AdminError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/admin/upload/pdf")
async def admin_upload_pdf(file: UploadFile = File(...)):
    try:
        content = await file.read()
        return admin.save_uploaded_pdf(file.filename, content)
    except admin.AdminError as e:
        raise HTTPException(status_code=400, detail=str(e))


_reindex_lock = threading.Lock()


@app.post("/admin/reindex")
def admin_reindex():
    """Rebuilds the FAISS index from whatever's currently in data/, then
    reloads it into this running server's memory -- plus refreshes the
    eligibility filter's cache -- so CRUD changes actually show up in chat
    answers and eligibility results without a server restart."""
    global vectorstore
    if not _reindex_lock.acquire(blocking=False):
        raise HTTPException(status_code=409, detail="A reindex is already running. Wait for it to finish.")
    try:
        try:
            stats = admin.rebuild_search_index()
        except Exception as e:
            # The old index on disk and in memory are untouched, so chat keeps working.
            raise HTTPException(status_code=500, detail=f"Reindex failed: {e}")
        try:
            vectorstore = load_index()
            eligibility.load_dataframe(force_reload=True)
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Index was rebuilt but reloading it failed ({e}). Restart the server.",
            )
        return {"status": "reindexed", **stats}
    finally:
        _reindex_lock.release()
