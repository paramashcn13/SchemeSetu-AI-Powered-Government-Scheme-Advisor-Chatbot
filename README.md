# SchemeSetu

A source-grounded RAG assistant for Indian government welfare schemes. Ask
a question, get an answer generated only from real scheme records, with
citations back to the source — plus a structured eligibility filter for
"what am I actually eligible for" questions that don't need a chat at all.

Data source: ~3,400 scheme records scraped from myScheme.gov.in
(`data/updated_data.csv`), with optional PDF support.

## What's built

| Feature | Status |
|---|---|
| RAG pipeline (retrieval + Gemini answer generation) | ✅ Done |
| Source citations on every answer | ✅ Done |
| Confidence-scored retrieval + "no match found" fallback | ✅ Done, tested |
| Named-scheme filtering (e.g. "PM-KISAN" resolves to the right record) | ✅ Done |
| Multi-turn memory (follow-ups like "what documents do I need for that?") | ✅ Done, tested end-to-end |
| Eligibility-based filtering (age/income/state/category) | ✅ Done, backend + frontend, tested end-to-end |
| Admin dashboard (upload/manage scheme data without touching code) | ⬜ Not started |
| PostgreSQL (persisted accounts/history across sessions) | ⬜ Not started |
| Deployment | ⬜ Not started — runs on localhost only |

The last three are deliberately deferred, not abandoned — the current focus
was the four core features above.

## Setup

### Backend

```bash
cd files                        # or wherever app.py lives in your clone
python -m venv venv
venv\Scripts\activate           # Windows
# source venv/bin/activate      # macOS/Linux

pip install -r requirements.txt

copy .env.example .env          # Windows  (cp on macOS/Linux)
# open .env and set:
#   GEMINI_API_KEY  - your real Gemini key

# Add scheme data to data/ — either updated_data.csv (the myScheme CSV
# dump) or individual scheme PDFs, or both.

python ingest.py                # builds faiss_index/ — rerun whenever
                                 # data/ or ingest.py changes

uvicorn app:app --reload        # starts the API on http://127.0.0.1:8000
```

Windows PowerShell start sequence from the project root:

```powershell
.\venv\Scripts\Activate.ps1
cd files
uvicorn app:app --reload
```

Visit `http://127.0.0.1:8000/docs` for the interactive Swagger UI to test
endpoints directly without the frontend.

### Frontend

```bash
cd frontend
npm install
npm run dev                     # starts on http://localhost:5173
```

The frontend expects the backend running at `http://127.0.0.1:8000` — see
`API_URL`, `ELIGIBILITY_URL`, and `ELIGIBILITY_OPTIONS_URL` near the top of
`App.jsx` (and `BASE_URL` in `AdminPage.jsx`) if you need to point it elsewhere.

Chat is at `http://localhost:5173`, the admin dashboard at
`http://localhost:5173/admin`.

### Quick backend-only test (no frontend needed)

```bash
python rag_chat.py              # terminal chat loop, tests RAG + memory
python test_eligibility.py      # standalone eligibility filter test
python test_api.py              # 77 API tests (auth, CRUD, uploads, reindex, errors,
                                # languages, translate-first pipeline); needs no
                                # internet, FAISS or Gemini key
cd frontend && node test_i18n_voice.mjs   # UI-string coverage + voice helper logic
```

## API endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | Health check |
| `POST` | `/ask` | RAG chat — `{question, history, language}` → `{answer, sources, is_fallback, english_question}` |
| `GET` | `/languages` | Supported language codes |
| `POST` | `/translate` | `{text, source_language, language}` → `{translation}` (used for answers and scheme text) |
| `POST` | `/translate/batch` | `{texts, source_language, language}` → `{translations}` (eligibility cards and comparison) |
| `GET` | `/eligibility/options` | States list + category labels for the filter form |
| `POST` | `/eligibility` | `{age, income, state, category}` (all optional) → `{total_matched, returned, matches}` |

Admin endpoints are available in this local development app:

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/admin/schemes?search=&page=&page_size=` | List / search / paginate |
| `GET` | `/admin/schemes/{slug}` | One scheme |
| `POST` | `/admin/schemes` | Create (slug auto-generated if blank) |
| `PUT` | `/admin/schemes/{slug}` | Update (slug is immutable) |
| `DELETE` | `/admin/schemes/{slug}` | Delete |
| `POST` | `/admin/upload/csv` | Replace the whole CSV (validated first; bad files are rejected) |
| `POST` | `/admin/upload/pdf` | Add a PDF to `data/` |
| `POST` | `/admin/reindex` | Rebuild FAISS and refresh the eligibility cache |

Status codes you may see on `/ask`: `429` (Gemini quota reached), `503` (Gemini
unreachable), `400` (blank question), `500` (unexpected — details are logged
server-side, not shown to the user).

## What to test

1. **A question the data actually covers** — e.g. "Who is eligible for
   PM-KISAN?" — confirm the answer is correct and cites the right scheme.
2. **An unrelated question** — e.g. "What's the capital of France?" —
   confirm it says it couldn't find the info rather than guessing. This is
   the confidence-threshold fallback.
3. **A follow-up question** — ask about a scheme, then ask "what documents
   do I need for that?" without naming the scheme again. Check the backend
   terminal for `[debug] named scheme filter: ... (resolved from history)`.
4. **Eligibility filter** — click "Check my eligibility" in the sidebar,
   fill in a partial profile, confirm results are real scheme matches with
   working "Ask about this" buttons that hand off into the chat.
5. **Watch the `[debug] top retrieval confidence` line** printed for every
   `/ask` call. If real questions are scoring below `CONFIDENCE_THRESHOLD`
   (0.45 by default, in `rag_chat.py`), tune that value against your data.

## Project structure

```
files/
├── data/
│   └── updated_data.csv      # scheme records (not committed to git)
├── faiss_index/               # generated by ingest.py (not committed)
├── app.py                     # FastAPI app: /ask, /eligibility/*, /admin/*
├── rag_chat.py                # retrieval + Gemini answer engine, multi-turn memory
├── ingest.py                  # builds the FAISS index from CSV/PDF
├── eligibility.py             # fast keyword/regex filter over scheme data (no LLM calls)
├── admin.py                   # CRUD over the CSV, uploads, reindex
├── test_eligibility.py        # standalone test script for eligibility.py
├── test_api.py                # API tests with stubbed AI/search libraries
├── TEST_CASES.md              # formal test-case table (automated + manual)
├── requirements.txt
├── .env.example
├── .gitignore
└── frontend/
    ├── test_i18n_voice.mjs     # UI-string coverage + voice helper tests (node)
    └── src/
        ├── App.jsx             # React UI: chat thread + eligibility form/results
        ├── AdminPage.jsx       # /admin dashboard
        ├── i18n.js             # 10-language UI strings + helper
        ├── voice.js            # speech-to-text / read-aloud wrappers
        └── index.css           # navy/ivory/IBM Plex design system
```

## How the eligibility filter works

`data/updated_data.csv` has no structured age/income/state columns — only
free-text `eligibility`, `details`, `application`, `schemeCategory`, and
`tags`. `eligibility.py` extracts what it can via regex (age ranges, income
ceilings, state names) and applies a "benefit of the doubt" rule: if a
scheme's text doesn't explicitly mention a constraint, the filter does
**not** exclude it — it's included, on the assumption the person should read
the real eligibility text rather than be silently filtered out by a
regex miss. It's a fast, zero-LLM-call filter (~0.05s across all 3,400 rows
after a one-time load), not a semantic search or a legal determination —
the UI says so explicitly.

## Regional languages and voice

**How answers in other languages work (translate-first).** The embedding model
and the scheme data are English-only, so for a non-English question the server
(1) translates it to English with one small Gemini call, (2) retrieves exactly as
before, and (3) asks Gemini to write the final answer in the chosen language. Because
retrieval is still English-vs-English, the 0.45 confidence threshold means the same
thing in every language. Cost: two Gemini calls per non-English question (one if
the user typed plain English). The "not found" message is a fixed, pre-translated
string per language, so it costs no quota and never gets garbled; the model signals
"not enough context" with the token `NO_INFO_FOUND`, which the server swaps for it.

**Follow-ups.** The server returns `english_question`, and the frontend sends
*that* back as history, so "what documents do I need for that?" still resolves
the scheme name in any language.

**Eligibility cards and comparison details** are translated together in one
Gemini request per result set, avoiding a burst of per-card translation calls.

**Voice** uses the browser's built-in Web Speech API — no extra keys or backend.
Speech-to-text works in Chrome/Edge and needs internet; read-aloud depends on
voices installed on the device (Android/Chrome usually has all ten; some Windows
PCs lack Tamil/Telugu/etc.). Unsupported browsers (e.g. Firefox) get a message and
everything else keeps working.

**Fonts.** `index.css` loads Noto Sans faces for the eight Indian scripts from Google
Fonts; offline, the OS fallback fonts are used.

**Translation quality.** Interface strings (`frontend/src/i18n.js`) were drafted with
AI assistance and should be reviewed by a native speaker before a public demo.
Scheme names, state names and category labels are shown in English.

## Admin dashboard

Open `/admin` to add / edit / delete schemes, upload a
replacement CSV or a PDF, and click **Reindex**. Edits are written to
`data/updated_data.csv` immediately (via a temp file, so a crash cannot corrupt
it) but **do not appear in chat or eligibility until you click Reindex** — that
is deliberate, because reindexing re-embeds everything and takes a while. If a
reindex fails, the previous index stays live and chat keeps working.

## Known limitations

- The eligibility filter is regex based: ~54% of income ceilings and some age
  limits cannot be extracted, so it over-includes by design. It is a first-pass
  filter, not a legal determination.
- Eligibility results are capped at 25, with no pagination.
- Reindex rebuilds the whole FAISS index and blocks until done.
- Chat history and bookmarks are saved in this browser's local storage.
- Embeddings are English-only; other languages work through translation, so a
  mistranslated question can retrieve the wrong scheme.
- Gemini quota can be exhausted by answers and translations. The app shows a
  localized quota message and batches eligibility-card translations.
- Scheme names and official document names remain in their source language.
- Voice quality and availability depend on the browser and device.

## Next steps

1. **PostgreSQL and deployment** — deliberately deferred. The app currently
   stores chat history and bookmarks in the visitor's browser. Set `VITE_API_BASE`
   in the frontend and `ALLOWED_ORIGINS` in the backend for another environment.
