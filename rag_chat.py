import os
import re
import csv
import json
from pathlib import Path
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import google.generativeai as genai

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent   # so paths work from any working directory
INDEX_DIR = str(BASE_DIR / "faiss_index")
DATA_DIR = BASE_DIR / "data"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
# Verified as a valid stable model on ai.google.dev (Oct 2026). Override with
# GEMINI_MODEL in .env if Google retires it before your demo.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
CONFIDENCE_THRESHOLD = 0.45                
TOP_K = 4

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if not GEMINI_API_KEY:
    raise EnvironmentError(
        "GEMINI_API_KEY not found. Copy .env.example to .env and paste your key in."
    )
genai.configure(api_key=GEMINI_API_KEY)


# ---------------------------------------------------------------------------
# Regional-language support (translate-first design)
#
# The embedding model and the scheme data are English-only, so for any other
# language we: (1) translate the question to English, (2) retrieve in English
# exactly as before, (3) ask Gemini to write the answer in the user's language.
# The 0.45 confidence threshold stays valid because retrieval is still
# English-vs-English.
# ---------------------------------------------------------------------------
LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "ta": "Tamil",
    "te": "Telugu",
    "kn": "Kannada",
    "ml": "Malayalam",
    "mr": "Marathi",
    "bn": "Bengali",
    "gu": "Gujarati",
    "pa": "Punjabi",
}

FALLBACK_EN = (
    "I could not find this information in the available scheme documents. "
    "Try rephrasing your question or asking about a scheme that's loaded in the system."
)
FALLBACK_MESSAGES = {
    "en": FALLBACK_EN,
    "hi": "मुझे उपलब्ध योजना दस्तावेज़ों में यह जानकारी नहीं मिली। कृपया अपना प्रश्न दूसरे शब्दों में पूछें या सिस्टम में उपलब्ध किसी योजना के बारे में पूछें।",
    "ta": "கிடைக்கும் திட்ட ஆவணங்களில் இந்தத் தகவலை என்னால் கண்டறிய முடியவில்லை. உங்கள் கேள்வியை வேறு விதமாகக் கேளுங்கள் அல்லது அமைப்பில் உள்ள ஒரு திட்டத்தைப் பற்றிக் கேளுங்கள்.",
    "te": "అందుబాటులో ఉన్న పథకం పత్రాలలో ఈ సమాచారం నాకు కనిపించలేదు. దయచేసి మీ ప్రశ్నను మరో విధంగా అడగండి లేదా సిస్టమ్‌లో ఉన్న ఏదైనా పథకం గురించి అడగండి.",
    "kn": "ಲಭ್ಯವಿರುವ ಯೋಜನೆ ದಾಖಲೆಗಳಲ್ಲಿ ಈ ಮಾಹಿತಿ ನನಗೆ ಸಿಗಲಿಲ್ಲ. ದಯವಿಟ್ಟು ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಬೇರೆ ರೀತಿಯಲ್ಲಿ ಕೇಳಿ ಅಥವಾ ವ್ಯವಸ್ಥೆಯಲ್ಲಿರುವ ಯಾವುದಾದರೂ ಯೋಜನೆಯ ಬಗ್ಗೆ ಕೇಳಿ.",
    "ml": "ലഭ്യമായ പദ്ധതി രേഖകളിൽ ഈ വിവരം കണ്ടെത്താനായില്ല. നിങ്ങളുടെ ചോദ്യം മറ്റൊരു രീതിയിൽ ചോദിക്കുകയോ സിസ്റ്റത്തിലുള്ള ഒരു പദ്ധതിയെക്കുറിച്ച് ചോദിക്കുകയോ ചെയ്യുക.",
    "mr": "उपलब्ध योजना दस्तऐवजांमध्ये ही माहिती मला सापडली नाही. कृपया तुमचा प्रश्न वेगळ्या शब्दांत विचारा किंवा प्रणालीमध्ये असलेल्या एखाद्या योजनेबद्दल विचारा.",
    "bn": "উপলব্ধ প্রকল্পের নথিতে এই তথ্য আমি খুঁজে পাইনি। অনুগ্রহ করে প্রশ্নটি অন্যভাবে জিজ্ঞাসা করুন অথবা সিস্টেমে থাকা কোনো প্রকল্প সম্পর্কে জিজ্ঞাসা করুন।",
    "gu": "ઉપલબ્ધ યોજનાના દસ્તાવેજોમાં મને આ માહિતી મળી નથી. કૃપા કરીને તમારો પ્રશ્ન બીજી રીતે પૂછો અથવા સિસ્ટમમાં ઉપલબ્ધ કોઈ યોજના વિશે પૂછો.",
    "pa": "ਉਪਲਬਧ ਯੋਜਨਾ ਦਸਤਾਵੇਜ਼ਾਂ ਵਿੱਚ ਮੈਨੂੰ ਇਹ ਜਾਣਕਾਰੀ ਨਹੀਂ ਮਿਲੀ। ਕਿਰਪਾ ਕਰਕੇ ਆਪਣਾ ਸਵਾਲ ਹੋਰ ਤਰੀਕੇ ਨਾਲ ਪੁੱਛੋ ਜਾਂ ਸਿਸਟਮ ਵਿੱਚ ਮੌਜੂਦ ਕਿਸੇ ਯੋਜਨਾ ਬਾਰੇ ਪੁੱਛੋ।",
}

# In non-English mode the model signals "context was not enough" with this
# token, which we swap for the localized fallback above (so the UI can show the
# fallback style and we never trust a free-form translation of the refusal).
NO_INFO_TOKEN = "NO_INFO_FOUND"
FALLBACK_PHRASE = "i could not find this information"


def normalise_language(language):
    code = (language or "en").strip().lower()
    return code if code in LANGUAGES else None


def _is_ascii(text):
    return all(ord(ch) < 128 for ch in text)


# Plain-ASCII text in a non-English chat is either genuine English or Indian
# language written in Roman letters (e.g. "kisan ke liye kaun si yojana hai"),
# which is what speech recognition sometimes returns. Real English questions
# nearly always contain one of these words; Hinglish/Tanglish almost never does.
# (Deliberately no "is", "me", "to", "do", "in", "a", "i": they are also Hindi words.)
ENGLISH_HINT_WORDS = {
    "the", "are", "what", "who", "how", "which", "for", "of", "and", "scheme",
    "schemes", "eligible", "eligibility", "benefits", "benefit", "apply",
    "documents", "document", "need", "there", "available", "about", "tell",
    "does", "with", "from", "my", "criteria", "required", "when", "where",
}


def _looks_english(text):
    words = set(re.findall(r"[a-z]+", text.lower()))
    return bool(words & ENGLISH_HINT_WORDS)


class LLMError(Exception):
    """Gemini could not produce an answer. `kind` is 'quota' or 'unavailable'
    so the API layer can return a helpful message instead of a bare 500."""

    def __init__(self, kind, message):
        super().__init__(message)
        self.kind = kind


def load_index():
    if not os.path.isdir(INDEX_DIR):
        raise FileNotFoundError(
            f"Search index not found at '{INDEX_DIR}'. Run `python ingest.py` once first."
        )
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
    return FAISS.load_local(
        INDEX_DIR, embeddings, allow_dangerous_deserialization=True
    )


def normalise(text):
    """Make names such as 'PM-KISAN' and 'pm kisan' comparable."""
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def find_named_scheme(vectorstore, question):
    """Return the indexed scheme explicitly named in a question, if any.

    This relies on the scheme name and CSV slug saved by the current ingest
    script.  A minimum alias length prevents short generic words from being
    mistaken for a scheme name.
    """
    normalised_question = f" {normalise(question)} "
    matches = []
    for doc in vectorstore.docstore._dict.values():
        source = doc.metadata.get("source")
        for alias in (doc.metadata.get("scheme_name"), doc.metadata.get("slug")):
            alias = normalise(alias)
            if len(alias) >= 4 and f" {alias} " in normalised_question:
                matches.append((len(alias), source))


    if not matches and DATA_DIR.is_dir():
        for filename in os.listdir(DATA_DIR):
            if not filename.lower().endswith(".csv"):
                continue
            with open(DATA_DIR / filename, encoding="utf-8-sig", newline="") as csv_file:
                for row in csv.DictReader(csv_file):
                    source = str(row.get("scheme_name") or "").strip()
                    for alias in (source, row.get("slug", "")):
                        alias = normalise(alias)
                        if len(alias) >= 4 and f" {alias} " in normalised_question:
                            matches.append((len(alias), source))

    return max(matches, default=(0, None))[1]



FOLLOWUP_HINTS = (
    "it", "that", "this", "the scheme", "same scheme", "above",
    "it's", "its", "those",
)


def looks_like_followup(question):
    """Heuristic: does this question read like it depends on prior context
    rather than standing alone? Used only to decide whether it's worth
    falling back to history -- history is also tried when no scheme is
    named at all, so this just helps logging/debugging stay honest."""
    normalised = f" {normalise(question)} "
    return any(f" {normalise(hint)} " in normalised for hint in FOLLOWUP_HINTS)


def resolve_scheme_with_history(vectorstore, question, history):
    """Work out which scheme (if any) this question is about, using the
    current question first and recent conversation history as a fallback.

    `history` is a list of {"question": str, "answer": str} dicts, oldest
    first. We only need it to recover the scheme a follow-up question like
    "what documents do I need for that?" implicitly refers to -- we do NOT
    use it to answer the question itself, only to pick which scheme's
    chunks to retrieve.
    """
    named_scheme = find_named_scheme(vectorstore, question)
    if named_scheme:
        return named_scheme, False  # (scheme, used_history)

    if not history:
        return None, False

    
    for turn in reversed(history):
        prior_question = turn.get("question", "")
        prior_scheme = find_named_scheme(vectorstore, prior_question)
        if prior_scheme:
            return prior_scheme, True

    return None, False


def retrieve(vectorstore, question, k=TOP_K, source=None):
    """Return (chunk, similarity_score) pairs. FAISS returns a DISTANCE
    (lower = more similar), so we convert it to a 0-1 'confidence' score
    where higher = more confident."""
    search_options = {"k": k}
    if source:
        search_options["filter"] = {"source": source}
        search_options["fetch_k"] = len(vectorstore.docstore._dict)
    results = vectorstore.similarity_search_with_score(question, **search_options)
    scored = []
    for doc, distance in results:
        confidence = 1 / (1 + distance)  
        scored.append((doc, confidence))
    return scored


MAX_HISTORY_TURNS = 3


def build_history_block(history):
    """Format the last few Q&A turns for the prompt. Returns "" if there's
    no history, so callers can drop the section entirely rather than
    printing an empty header."""
    if not history:
        return ""

    recent = history[-MAX_HISTORY_TURNS:]
    lines = []
    for turn in recent:
        prior_question = str(turn.get("question", "")).strip()
        prior_answer = str(turn.get("answer", "")).strip()
        if not prior_question:
            continue
        lines.append(f"User asked: {prior_question}")
        if prior_answer:
            lines.append(f"You answered: {prior_answer}")
    return "\n".join(lines)


def translate_to_english(question, language):
    """One small Gemini call. Skipped for English, and for text that is already
    plain English (the user picked Tamil but typed in English). Romanized
    Hindi/Tamil/etc. is NOT skipped -- it needs translating too."""
    if language == "en" or (_is_ascii(question) and _looks_english(question)):
        return question
    name = LANGUAGES[language]
    prompt = (
        f"Translate this question from {name} into English. It may be written in {name} script "
        f"or in Roman letters (transliterated). If it is already English, return it unchanged. "
        f"It will be used to search a "
        f"database of Indian government welfare schemes.\n"
        f"Rules: keep scheme names and acronyms (for example PM-KISAN) exactly as written, "
        f"and give a scheme named in {name} script its usual English name. "
        f"Do NOT answer the question. Output ONLY the English question.\n\n"
        f"Question: {question}"
    )
    translated = ask_gemini(prompt).strip().strip('"').strip()
    return translated or question


def translate_text(text, language, source_language="en"):
    """Translate text from `source_language` into `language`."""
    if not text.strip() or language == source_language:
        return text
    source_name = LANGUAGES[source_language]
    target_name = LANGUAGES[language]
    prompt = (
        f"Translate the following text from {source_name} into {target_name}. "
        f"Keep scheme names, acronyms, numbers and rupee amounts unchanged. "
        f"Do not add or remove information. Output ONLY the translation.\n\n{text}"
    )
    return ask_gemini(prompt).strip()


def translate_texts(texts, language, source_language="en"):
    """Translate a short list in one model request to avoid quota-heavy bursts."""
    if language == source_language:
        return texts
    if not texts:
        return []
    source_name = LANGUAGES[source_language]
    target_name = LANGUAGES[language]
    prompt = (
        f"Translate each string from {source_name} into {target_name}. Keep the order, "
        "scheme names, acronyms, numbers and rupee amounts. Do not add or remove information. "
        "Return ONLY a JSON array of translated strings with exactly the same length.\n\n"
        f"{json.dumps(texts, ensure_ascii=False)}"
    )
    result = ask_gemini(prompt).strip()
    result = re.sub(r"^```(?:json)?\s*|\s*```$", "", result, flags=re.IGNORECASE)
    try:
        translated = json.loads(result.strip())
    except json.JSONDecodeError as exc:
        raise LLMError("unavailable", "The AI service returned an invalid translation.") from exc
    if not isinstance(translated, list) or len(translated) != len(texts) or not all(isinstance(item, str) for item in translated):
        raise LLMError("unavailable", "The AI service returned an incomplete translation.")
    return translated


def build_prompt(question, scored_chunks, history=None, language="en"):
    context_blocks = []
    for i, (doc, score) in enumerate(scored_chunks, start=1):
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "?")
        context_blocks.append(
            f"[Chunk {i} | source: {source}, page: {page}]\n{doc.page_content}"
        )
    context_text = "\n\n".join(context_blocks)

    history_block = build_history_block(history)
    history_section = ""
    if history_block:
        history_section = f"""
Recent conversation (for phrasing and resolving references like "that
scheme" or "it" ONLY -- do not treat these prior answers as a source of
facts; the Context below is the only source of facts):
{history_block}
"""

    if language == "en":
        no_info_rule = (
            '- If the context does not contain enough information to answer, say clearly:\n'
            '  "I could not find this information in the available scheme documents."\n'
            '  Do NOT guess or make up an answer.'
        )
    else:
        name = LANGUAGES[language]
        no_info_rule = (
            f"- Write your ENTIRE answer in {name}. The context is in English: translate "
            f"faithfully and do not add facts. Keep scheme names, acronyms (like PM-KISAN) "
            f"and rupee amounts in their original form.\n"
            f"- If the context does not contain enough information to answer, reply with "
            f"exactly {NO_INFO_TOKEN} and nothing else. Do NOT guess or make up an answer."
        )

    prompt = f"""You are SchemeSetu, an assistant that answers questions about Indian
government welfare schemes STRICTLY using the context chunks provided below.

Rules:
- Only use information present in the context. Do not use outside knowledge.
{no_info_rule}
- Do NOT include a "Sources" section, source list, or document names in your
  answer text. The application displays sources separately -- just answer
  the question directly.
- Keep the answer concise and citizen-friendly (avoid jargon).
- If the question uses a pronoun or short reference like "it", "that", or
  "the scheme" and the recent conversation below makes clear which scheme
  is meant, answer about that scheme using the Context provided.
{history_section}
Context:
{context_text}

Question: {question}

Answer:"""
    return prompt


def ask_gemini(prompt):
    """Call Gemini. Any failure is converted to LLMError so callers (and the
    API) can react sensibly -- quota exhaustion is by far the likeliest one on
    the free tier."""
    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)
        text = response.text  # raises ValueError if the reply was blocked/empty
    except ValueError as exc:
        raise LLMError("unavailable", "Gemini returned no usable answer for this question.") from exc
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}"
        lowered = detail.lower()
        if "429" in lowered or "quota" in lowered or "resourceexhausted" in lowered or "rate limit" in lowered:
            raise LLMError("quota", "The AI service's usage limit was reached.") from exc
        raise LLMError("unavailable", f"The AI service could not be reached ({type(exc).__name__}).") from exc
    if not text or not text.strip():
        raise LLMError("unavailable", "Gemini returned an empty answer.")
    return text


def answer_question_full(vectorstore, question, history=None, language="en"):
    """Full pipeline. Returns a dict:
        answer, sources, is_fallback, english_question

    history: optional list of {"question", "answer"} dicts, oldest first. Used
    only to resolve follow-up references ("that scheme", "it") -- never as a
    source of facts. For non-English chats the caller should store
    `english_question` in history so scheme-name matching keeps working.
    """
    history = history or []
    language = normalise_language(language) or "en"
    fallback_text = FALLBACK_MESSAGES[language]

    english_question = translate_to_english(question, language)
    if english_question != question:
        print(f"[debug] translated ({language}): {english_question}")

    # Filled in as the pipeline runs; handed back so app.py can log fallbacks
    # (6.4 data-gap log). AskResponse ignores these two extra keys.
    top_confidence = None
    named_scheme = None

    def fallback():
        return {"answer": fallback_text, "sources": [], "is_fallback": True,
                "english_question": english_question,
                "top_confidence": top_confidence, "named_scheme": named_scheme}

    named_scheme, used_history = resolve_scheme_with_history(vectorstore, english_question, history)

    # A follow-up such as "what documents do I need for that?" has almost no
    # useful retrieval vocabulary on its own.  Once history has identified the
    # scheme, include that name in the search query as well as filtering to its
    # records.  This keeps the confidence check meaningful for follow-ups.
    retrieval_question = english_question
    if used_history and named_scheme:
        retrieval_question = f"{named_scheme}: {english_question}"

    scored_chunks = retrieve(vectorstore, retrieval_question, source=named_scheme)

    if not scored_chunks:
        return fallback()

    top_confidence = scored_chunks[0][1]
    print(f"\n[debug] top retrieval confidence: {top_confidence:.3f}")
    if named_scheme:
        print(f"[debug] named scheme filter: {named_scheme}"
              + (" (resolved from history)" if used_history else ""))
    print("[debug] all retrieved chunks:")
    for doc, score in scored_chunks:
        print(f"  {score:.3f}  {doc.metadata.get('source', 'unknown')}")

    if top_confidence < CONFIDENCE_THRESHOLD:
        return fallback()

    prompt = build_prompt(english_question, scored_chunks, history=history, language=language)
    answer = ask_gemini(prompt)

    if language != "en" and NO_INFO_TOKEN in answer:
        return fallback()

    sources = sorted(set(
        f"{doc.metadata.get('source', 'unknown')} (page {doc.metadata.get('page', '?')})"
        for doc, score in scored_chunks
    ))
    return {
        "answer": answer,
        "sources": sources,
        "is_fallback": FALLBACK_PHRASE in answer.lower(),
        "english_question": english_question,
        "top_confidence": top_confidence,
        "named_scheme": named_scheme,
    }


def answer_question(vectorstore, question, history=None):
    """Backwards-compatible English wrapper used by the CLI: (answer, sources)."""
    result = answer_question_full(vectorstore, question, history=history, language="en")
    return result["answer"], result["sources"]


def main():
    print("Loading FAISS index...")
    vectorstore = load_index()
    print("Ready. Ask a question about a loaded scheme (or type 'exit').\n")

    history = []  

    while True:
        question = input("You: ").strip()
        if question.lower() in ("exit", "quit"):
            break
        if not question:
            continue

        try:
            answer, sources = answer_question(vectorstore, question, history=history)
        except LLMError as exc:
            print(f"\n[error] {exc}\n")
            continue
        print(f"\nSchemeSetu: {answer}")
        if sources:
            print("\nSources:")
            for s in sources:
                print(f"  - {s}")
        print()

        history.append({"question": question, "answer": answer})
        history = history[-MAX_HISTORY_TURNS:]


if __name__ == "__main__":
    main()
