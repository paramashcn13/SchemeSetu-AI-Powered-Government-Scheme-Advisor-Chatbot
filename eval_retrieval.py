"""Evaluate FAISS retrieval against a small, hand-labelled question set.

Usage (from files/):
    python eval_retrieval.py
    python eval_retrieval.py --questions eval_questions.json --k 4
    python eval_retrieval.py --thresholds 0.30,0.40,0.45,0.50,0.60

No Gemini calls are made. A Gemini key is not required for this retrieval-only
check; the evaluator supplies a placeholder only if rag_chat needs one while
loading its shared retrieval helpers.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_QUESTIONS = BASE_DIR / "eval_questions.json"


def parse_thresholds(raw: str) -> list[float]:
    try:
        values = sorted({float(part.strip()) for part in raw.split(",") if part.strip()})
    except ValueError as exc:
        raise argparse.ArgumentTypeError("thresholds must be comma-separated numbers") from exc
    if not values or any(value < 0 or value > 1 for value in values):
        raise argparse.ArgumentTypeError("provide one or more thresholds between 0 and 1")
    return values


def load_questions(path: Path) -> list[dict]:
    try:
        questions = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Could not read question set {path}: {exc}") from exc
    if not isinstance(questions, list) or not questions:
        raise SystemExit("Question file must contain a non-empty JSON array.")
    for number, row in enumerate(questions, 1):
        if not isinstance(row, dict) or not str(row.get("question", "")).strip():
            raise SystemExit(f"Question {number} needs a non-empty 'question'.")
        expected = row.get("expected_sources", [])
        if isinstance(expected, str):
            expected = [expected]
            row["expected_sources"] = expected
        if not isinstance(expected, list) or not expected:
            raise SystemExit(f"Question {number} needs at least one expected_sources entry.")
    return questions


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", type=Path, default=DEFAULT_QUESTIONS)
    parser.add_argument("--k", type=int, default=None, help="number of chunks to retrieve (defaults to rag_chat.TOP_K)")
    parser.add_argument(
        "--thresholds",
        type=parse_thresholds,
        default=parse_thresholds("0.30,0.35,0.40,0.45,0.50,0.55,0.60,0.65"),
        help="confidence cutoffs to compare, e.g. 0.35,0.45,0.55",
    )
    parser.add_argument("--details", action="store_true", help="print each question's top source and confidence")
    args = parser.parse_args()

    load_dotenv(BASE_DIR / ".env")
    os.environ.setdefault("GEMINI_API_KEY", "retrieval-only-no-gemini-call")
    # Import after the local env is loaded; rag_chat configures the SDK at import,
    # but no generative method is called in this script.
    from rag_chat import TOP_K, load_index, retrieve

    questions = load_questions(args.questions)
    k = args.k or TOP_K
    if k < 1:
        parser.error("--k must be at least 1")

    print("Loading the FAISS index and embedding model...")
    vectorstore = load_index()
    evaluated = []
    for row in questions:
        hits = retrieve(vectorstore, row["question"], k=k)
        expected = {str(value).strip().casefold() for value in row["expected_sources"]}
        sources = [str(doc.metadata.get("source", "")).strip() for doc, _ in hits]
        matched = any(source.casefold() in expected for source in sources)
        top_confidence = hits[0][1] if hits else 0.0
        evaluated.append((row, sources, matched, top_confidence))

    total = len(evaluated)
    baseline_hits = sum(1 for _, _, matched, _ in evaluated if matched)
    print(f"\nRetrieval hit@{k}: {baseline_hits}/{total} ({baseline_hits / total:.1%})")
    if args.details:
        for row, sources, matched, confidence in evaluated:
            top = sources[0] if sources else "(no result)"
            mark = "HIT" if matched else "MISS"
            print(f"  {mark}  top={confidence:.3f}  {top}  |  {row['question']}")

    print("\nThreshold sweep (accepted means top confidence >= threshold)")
    print(" threshold | accepted | hits | hit rate / all | hit rate / accepted")
    for threshold in args.thresholds:
        accepted = [result for result in evaluated if result[3] >= threshold]
        hits = sum(1 for result in accepted if result[2])
        all_rate = hits / total
        accepted_rate = hits / len(accepted) if accepted else 0.0
        print(f"   {threshold:0.2f}    | {len(accepted):>3}/{total:<3} | {hits:>3}  |    {all_rate:6.1%}     |       {accepted_rate:6.1%}")

    print("\nA hit means at least one expected scheme is in the top-k chunks. The 'all' rate is coverage-aware; the 'accepted' rate measures precision among questions that pass the cutoff.")
    print("Use a larger, representative labelled question set before changing CONFIDENCE_THRESHOLD.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
