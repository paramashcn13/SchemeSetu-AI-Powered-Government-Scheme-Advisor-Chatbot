# SchemeSetu — Test Cases

Three parts: **A. automated backend** (`python test_api.py`, 77 tests, no internet/FAISS/Gemini needed), **B. automated frontend logic** (`node test_i18n_voice.mjs`, run from `frontend/`), and **C. manual** (needs your machine: real FAISS index, Gemini key, browser, microphone). Fill in *Actual* and *Result* for part C as you run them.

## A. Automated backend tests (77)

| ID | Test (input → expected behaviour) | Result |
|---|---|---|
| API-01 | Health check returns running status | PASS |
| ASK-01 | Valid question returns answer + sources | PASS |
| ASK-02 | Blank question is rejected with 400 | PASS |
| ASK-03 | Oversized question is rejected with 422 | PASS |
| ASK-04 | Gemini quota error becomes HTTP 429 with readable message | PASS |
| ASK-05 | Gemini outage becomes HTTP 503 | PASS |
| ASK-06 | Unexpected error becomes 500 without leaking internals | PASS |
| LLM-01 | ask_gemini returns text on success | PASS |
| LLM-02 | 429 / quota exception is classified as 'quota' | PASS |
| LLM-03 | Network failure is classified as 'unavailable' | PASS |
| LLM-04 | Blocked/empty Gemini reply is classified as 'unavailable' | PASS |
| ELIG-01 | Options endpoint lists states and 7 categories | PASS |
| ELIG-02 | Farmer in Tamil Nadu gets central + TN schemes, not Kerala | PASS |
| ELIG-03 | State filter excludes other states' State-level schemes | PASS |
| ELIG-04 | Age 25 excluded from 'above 60' scheme, included in 18-60 scheme | PASS |
| ELIG-05 | Income above a scheme's ceiling excludes it | PASS |
| ELIG-06 | Scheme with no stated constraints is kept (benefit of the doubt) | PASS |
| ELIG-07 | Empty profile returns every scheme | PASS |
| ELIG-08 | Impossible age is rejected with 422 | PASS |
| ELIG-09 | Match objects expose the 'category' key | PASS |
| ADM-01 | Admin routes are available in local development | PASS |
| ADM-05 | Create scheme auto-generates slug and defaults blank level to Central | PASS |
| ADM-06 | Duplicate name gets a unique slug (-2) | PASS |
| ADM-07 | Create without scheme_name -> 422 | PASS |
| ADM-08 | Create with whitespace-only name -> 400 | PASS |
| ADM-09 | Update changes fields but slug stays immutable | PASS |
| ADM-10 | Get one scheme by slug | PASS |
| ADM-11 | Unknown slug -> 404 | PASS |
| ADM-12 | Search filters the list | PASS |
| ADM-13 | Invalid page number -> 400 (not a crash) | PASS |
| ADM-14 | Delete removes the scheme | PASS |
| ADM-15 | Deleting twice -> 404 | PASS |
| ADM-16 | Writes leave no .tmp file behind | PASS |
| UP-01 | Non-.csv filename -> 400 | PASS |
| UP-02 | Empty CSV -> 400 | PASS |
| UP-03 | CSV without scheme_name column -> 400 | PASS |
| UP-04 | Binary garbage CSV -> 400 | PASS |
| UP-05 | CSV with no usable rows -> 400 | PASS |
| UP-06 | All rejected uploads left the existing CSV untouched | PASS |
| UP-07 | Valid CSV replaces data, missing columns filled, unique slugs generated | PASS |
| UP-08 | Fake PDF content -> 400 | PASS |
| UP-09 | Valid PDF saved with folder parts stripped (no path traversal) | PASS |
| RIX-01 | New scheme is NOT visible in eligibility before Reindex (deliberate) | PASS |
| RIX-02 | Reindex succeeds and reports counts | PASS |
| RIX-03 | After Reindex the new scheme appears in eligibility results | PASS |
| RIX-04 | Reindex failure -> 500 with explanation, server stays up | PASS |
| RIX-05 | Chat/eligibility still work after a failed Reindex | PASS |
| RIX-06 | A second Reindex while one is running -> 409 | PASS |
| RIX-07 | The first Reindex still completes | PASS |
| RIX-08 | Reindex route is available in local development | PASS |
| LANG-01 | /ask forwards language and returns english_question + is_fallback | PASS |
| LANG-02 | Unsupported language on /ask -> 400 | PASS |
| LANG-03 | Language defaults to English when omitted | PASS |
| LANG-04 | /languages lists the 10 supported languages | PASS |
| LANG-05 | /translate returns a translation | PASS |
| LANG-06 | /translate rejects unsupported language (400) | PASS |
| LANG-07 | /translate rejects blank text (400) | PASS |
| LANG-08 | /translate rejects oversized text (422) | PASS |
| LANG-09 | /translate maps quota error to 429 | PASS |
| LANG-10 | /translate hides unexpected errors behind a 500 | PASS |
| LANG-11 | Every language has a localized fallback message; non-English ones differ from English | PASS |
| PIPE-01 | Tamil question is translated to English and retrieval uses the English text | PASS |
| PIPE-02 | Named-scheme filter still works on the translated question | PASS |
| PIPE-03 | Answer prompt asks for Tamil and carries the NO_INFO rule | PASS |
| PIPE-04 | Plain-English question in Tamil mode skips the translate call (saves quota) | PASS |
| PIPE-05 | English mode makes exactly one Gemini call and keeps the original English prompt | PASS |
| PIPE-06 | Model says NO_INFO_FOUND -> localized Tamil fallback, is_fallback, no sources | PASS |
| PIPE-07 | Low retrieval confidence -> localized Hindi fallback WITHOUT calling the answer model | PASS |
| PIPE-08 | Tamil follow-up resolves to the scheme from English history | PASS |
| PIPE-09 | English answer containing the refusal phrase is flagged is_fallback | PASS |
| PIPE-10 | Normal answer is not flagged as fallback and lists its source | PASS |
| PIPE-11 | translate_text('en') returns text unchanged without calling Gemini | PASS |
| PIPE-12 | translate_text keeps numbers/names instruction and returns model output | PASS |
| PIPE-13 | Quota error during the translate step surfaces as LLMError('quota') | PASS |

Notes: eligibility tests use a 4-row synthetic CSV, not your real 3,400-row file. Reindex tests stub the embedding step (they prove locking, cache reload and failure handling, not FAISS itself). LANG-/PIPE- tests run the real `rag_chat.py` pipeline against a fake search index and a fake Gemini that records every prompt, so they prove *what is sent to Gemini* (translate step, answer-language rule, NO_INFO fallback, English history) but not translation quality.

## B. Automated frontend logic (`frontend/test_i18n_voice.mjs`)

Checks that: all 10 languages exist; every language has every UI string (except three intentionally English-only error strings); placeholders `{n}` / `{lang}` survive translation; headings are actually translated; `t()` falls back to English for missing keys; markdown is stripped before read-aloud; long answers are split into ≤180-char chunks without losing words; Hindi/Bengali/Punjabi sentence-end marks (।) split correctly; voice helpers do not crash when the browser lacks speech APIs. Result when run: **ALL PASSED**.

## C. Manual tests (run locally)

| ID | Steps / input | Expected | Actual | Result |
|---|---|---|---|---|
| C-01 | Chat: “Who is eligible for PM-KISAN?” | Correct eligibility text; source card names the PM-KISAN record |  |  |
| C-02 | Chat: “What's the capital of France?” | Fallback message, no sources, console confidence < 0.45 |  |  |
| C-03 | Ask about PM-KISAN, then “What documents do I need for that?” | Answer about PM-KISAN; backend prints `(resolved from history)` |  |  |
| C-04 | New policy question, then “what about that scheme?” | No stale context carried over |  |  |
| C-05 | Eligibility modal: age 45, income 150000, Tamil Nadu, Farmer; click “Ask about this” | Cards appear; button asks the chat and gets a grounded answer |  |  |
| C-06 | /admin: create “Test Setu Yojana” → Reindex → ask chat → eligibility check → delete → Reindex | Appears after Reindex; gone after delete + Reindex |  |  |
| C-07 | Stop the backend, ask a question | “Can't reach the SchemeSetu server…” with Try again |  |  |
| C-08 | Wrong GEMINI_API_KEY (or exhausted quota), restart, ask | Friendly “AI service busy/unavailable”, server stays up |  |  |
| C-09 | Switch languages after receiving an answer | Existing question, answer and result-card text translate; a quota error is shown if Gemini rejects translation |  |  |
| C-10 | /admin: upload a CSV with no scheme_name column | Confirm dialog, then red banner; list unchanged |  |  |
| L-01 | Select தமிழ். Click the farmers category in the sidebar | Whole UI is Tamil; answer is written in Tamil; source cards shown |  |  |
| L-02 | Tamil selected; type a Tamil question about PM-KISAN | Tamil answer; backend console shows `[debug] translated (ta): …` |  |  |
| L-03 | After L-02 ask in Tamil “அதற்கு என்ன ஆவணங்கள் தேவை?” | Resolved to PM-KISAN (console: `resolved from history`); Tamil answer |  |  |
| L-04 | Tamil selected; ask an unrelated Tamil question (weather) | Tamil fallback message in the grey fallback style, no sources |  |  |
| L-05 | Repeat one question in each of hi, te, kn, ml, mr, bn, gu, pa | Each renders in the correct script (no empty boxes) and the answer is in that language |  |  |
| L-06 | Hindi selected; run an eligibility check | Result-card snippets translate in a single batch; original text can be toggled on a card |  |  |
| L-07 | With a translated card showing, switch language to Tamil | Card resets to original English; Translate now produces Tamil |  |  |
| L-08 | Switch language, refresh the page | Selected language is remembered |  |  |
| L-09 | Tamil selected; stop backend; ask | Offline error message appears in Tamil |  |  |
| L-10 | Hindi selected; type the question in English | Answer comes back in Hindi (no translate call needed) |  |  |
| V-01 | Chrome: choose Tamil, tap mic, speak a Tamil question | Words appear in the box while speaking; tap stop; text stays; press send |  |  |
| V-02 | Type “PM-KISAN” in the box, then use mic | Spoken words are appended after the typed text |  |  |
| V-03 | Block microphone permission, tap mic | Message about microphone access; app still usable |  |  |
| V-04 | Tap mic and stay silent | “I didn't hear anything” message |  |  |
| V-05 | Tap Listen under an answer (Hindi, then Tamil) | Answer is read aloud; button shows Stop; Stop ends speech |  |  |
| V-06 | While an answer is being read, ask a new question / start a new chat / switch language | Audio stops immediately |  |  |
| V-07 | Long answer (>5 sentences) read aloud | Reads to the end without cutting off after ~15 s |  |  |
| V-08 | Device with no voice for the language (e.g. no Tamil voice) | Note that no voice was found; no crash |  |  |
| V-09 | Firefox: tap mic | “Voice input isn't supported…” message; chat, translate and Listen still work |  |  |
| V-10 | Listen on a bulleted answer | No “asterisk” / symbols spoken |  |  |
| U-01 | Resize to phone width; open sidebar, eligibility modal, language dropdown, /admin | Nothing overflows; language dropdown reachable |  |  |
