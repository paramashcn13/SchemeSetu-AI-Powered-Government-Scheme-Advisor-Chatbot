"""
gaplog.py -- 6.4 data-gap log.

Every /ask that ends in the "I couldn't find that" fallback is appended to
data/unanswered_log.jsonl (one JSON object per line). The admin dashboard reads
it back grouped by question, so the admin can see what people keep asking that
the data cannot answer, and add schemes for it.

Deliberately simple and a natural first table once PostgreSQL arrives.
Nothing here can break /ask: log_gap() swallows its own errors.

What is stored: timestamp, the question as typed, its English translation, the
language code, the top retrieval confidence, and the scheme name the question
resolved to (if any). No chat history, no IP address, no account.

Set GAP_LOG_PATH to point the log somewhere else (the tests do this so they
never touch your real log).
"""

import json
import os
import re
import threading
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_LOG_PATH = Path(__file__).resolve().parent / "data" / "unanswered_log.jsonl"
MAX_QUESTION_CHARS = 500
_lock = threading.Lock()


def log_path() -> Path:
    override = os.getenv("GAP_LOG_PATH")
    return Path(override) if override else DEFAULT_LOG_PATH


def normalise_question(text: str) -> str:
    """Lower-case, drop punctuation, collapse spaces, so "Scheme for tailors?"
    and "scheme for tailors" count as the same question."""
    # Keep letters, combining marks (Hindi/Tamil/... vowel signs and joiners are
    # marks, which a plain \w would strip), digits and spaces; drop punctuation.
    kept = "".join(
        ch if unicodedata.category(ch)[0] in "LMN" or ch.isspace() else " "
        for ch in (text or "").lower()
    )
    return re.sub(r"\s+", " ", kept).strip()


def log_gap(question, english_question="", language="en", top_confidence=None, named_scheme=None):
    """Append one unanswered question. Never raises."""
    try:
        question = (question or "").strip()[:MAX_QUESTION_CHARS]
        if not question:
            return False
        entry = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "question": question,
            "english_question": (english_question or question).strip()[:MAX_QUESTION_CHARS],
            "language": language or "en",
            "top_confidence": round(float(top_confidence), 3) if top_confidence is not None else None,
            "named_scheme": named_scheme or None,
        }
        path = log_path()
        with _lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return True
    except Exception as e:  # logging must never take /ask down
        print(f"[warn] gap log write failed: {type(e).__name__}: {e}")
        return False


def read_entries():
    """All well-formed log lines, oldest first. Bad lines are skipped."""
    path = log_path()
    if not path.exists():
        return []
    entries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, dict) and item.get("question"):
                entries.append(item)
    return entries


def summarise(limit: int = 100):
    """Group repeated questions. Most-asked first, ties broken by most recent.

    Returns {total_entries, unique_questions, gaps: [{question, original_question,
    count, first_seen, last_seen, languages, best_confidence, named_scheme}]}.
    """
    entries = read_entries()
    groups = {}
    for e in entries:
        english = e.get("english_question") or e["question"]
        key = normalise_question(english) or normalise_question(e["question"])
        if not key:
            continue
        groups.setdefault(key, []).append(e)

    gaps = []
    for items in groups.values():
        latest = items[-1]  # the log is append-only, so the last line is the newest (ts only has 1s resolution)
        confidences = [x["top_confidence"] for x in items if isinstance(x.get("top_confidence"), (int, float))]
        schemes = Counter(x["named_scheme"] for x in items if x.get("named_scheme"))
        gaps.append({
            "question": latest.get("english_question") or latest["question"],
            "original_question": latest["question"],
            "count": len(items),
            "first_seen": min(x.get("ts", "") for x in items),
            "last_seen": max(x.get("ts", "") for x in items),
            "languages": sorted({x.get("language") or "en" for x in items}),
            "best_confidence": max(confidences) if confidences else None,
            "named_scheme": schemes.most_common(1)[0][0] if schemes else None,
        })

    gaps.sort(key=lambda g: g["last_seen"], reverse=True)          # recent first...
    gaps.sort(key=lambda g: g["count"], reverse=True)               # ...then most asked (stable)
    return {
        "total_entries": len(entries),
        "unique_questions": len(gaps),
        "gaps": gaps[:max(1, int(limit))],
    }
