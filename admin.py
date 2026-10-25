"""Admin CRUD helpers for SchemeSetu scheme records."""

from __future__ import annotations

import os
import re
from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent / "data"
CSV_PATH = DATA_DIR / "updated_data.csv"
CSV_COLUMNS = [
    "scheme_name",
    "slug",
    "details",
    "benefits",
    "eligibility",
    "application",
    "documents",
    "level",
    "schemeCategory",
    "tags",
]


class AdminError(ValueError):
    """Raised for invalid admin actions or missing records."""


def _ensure_data_dir() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)


def _ensure_csv_exists() -> None:
    _ensure_data_dir()
    if not CSV_PATH.exists():
        pd.DataFrame(columns=CSV_COLUMNS).to_csv(CSV_PATH, index=False, encoding="utf-8-sig")


def _coerce(value):
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    if not isinstance(value, str):
        value = str(value)
    return value.strip()


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None:
        df = pd.DataFrame(columns=CSV_COLUMNS)
    else:
        df = df.copy()
        for col in list(df.columns):
            if str(col).startswith("Unnamed:"):
                df = df.drop(columns=[col])
        for col in CSV_COLUMNS:
            if col not in df.columns:
                df[col] = ""
        df = df[CSV_COLUMNS]

    for col in CSV_COLUMNS:
        df[col] = df[col].map(_coerce).fillna("")

    return df.reset_index(drop=True)


def _read_df() -> pd.DataFrame:
    _ensure_csv_exists()
    try:
        df = pd.read_csv(CSV_PATH, encoding="utf-8-sig")
    except pd.errors.EmptyDataError:
        df = pd.DataFrame(columns=CSV_COLUMNS)
    return _normalize_df(df)


def _write_df(df: pd.DataFrame) -> None:
    """Write via a temp file and swap it in, so a crash mid-write cannot leave a
    half-written CSV."""
    _ensure_data_dir()
    tmp_path = CSV_PATH.with_name(CSV_PATH.name + ".tmp")
    try:
        _normalize_df(df).to_csv(tmp_path, index=False, encoding="utf-8-sig")
        os.replace(tmp_path, CSV_PATH)
    finally:
        tmp_path.unlink(missing_ok=True)


def _slugify(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        raise AdminError("Scheme name is required.")
    slug = re.sub(r"[^a-z0-9]+", "-", raw.lower())
    slug = slug.strip("-")
    return slug or "scheme"


def _unique_slug(base_slug: str, df: pd.DataFrame) -> str:
    slug = (base_slug or "scheme").strip("-") or "scheme"
    candidate = slug
    suffix = 2
    existing = set(df["slug"].fillna("").astype(str).str.strip().str.lower())
    while candidate.lower() in existing:
        candidate = f"{slug}-{suffix}"
        suffix += 1
    return candidate


def list_schemes(search: str | None = None, page: int = 1, page_size: int = 25):
    page = int(page or 1)
    page_size = int(page_size or 25)
    if page < 1:
        raise AdminError("Page must be at least 1.")
    if page_size < 1:
        raise AdminError("page_size must be at least 1.")

    df = _read_df()
    if search and search.strip():
        needle = search.strip().lower()
        mask = df.apply(
            lambda row: any(
                needle in str(row.get(col, "") or "").lower()
                for col in [
                    "scheme_name",
                    "slug",
                    "details",
                    "benefits",
                    "eligibility",
                    "schemeCategory",
                    "tags",
                ]
            ),
            axis=1,
        )
        df = df[mask].reset_index(drop=True)

    total = int(len(df))
    start = (page - 1) * page_size
    end = start + page_size
    rows = df.iloc[start:end].to_dict(orient="records")
    return {"schemes": rows, "total": total, "page": page, "page_size": page_size}


def get_scheme(slug: str):
    target = str(slug or "").strip()
    if not target:
        raise AdminError("Scheme slug is required.")

    df = _read_df()
    match = df[df["slug"].fillna("").astype(str).str.strip().str.lower() == target.lower()]
    if match.empty:
        raise AdminError(f"Scheme not found: {slug}")
    return match.iloc[0].to_dict()


def create_scheme(data: dict):
    if not isinstance(data, dict):
        raise AdminError("Scheme data must be a dictionary.")

    scheme_name = _coerce(data.get("scheme_name"))
    if not scheme_name:
        raise AdminError("scheme_name is required.")

    df = _read_df()
    raw_slug = _coerce(data.get("slug"))
    slug = _slugify(raw_slug) if raw_slug else _slugify(scheme_name)
    slug = _unique_slug(slug, df)

    record = {col: _coerce(data.get(col, "")) for col in CSV_COLUMNS}
    record["scheme_name"] = scheme_name
    record["slug"] = slug
    record["details"] = _coerce(data.get("details", ""))
    record["benefits"] = _coerce(data.get("benefits", ""))
    record["eligibility"] = _coerce(data.get("eligibility", ""))
    record["application"] = _coerce(data.get("application", ""))
    record["documents"] = _coerce(data.get("documents", ""))
    record["level"] = _coerce(data.get("level")) or "Central"  # blank (as the API sends it) -> Central
    record["schemeCategory"] = _coerce(data.get("schemeCategory", ""))
    record["tags"] = _coerce(data.get("tags", ""))

    df = pd.concat([df, pd.DataFrame([record])], ignore_index=True)
    _write_df(df)
    return record


def update_scheme(slug: str, changes: dict):
    target = str(slug or "").strip()
    if not target:
        raise AdminError("Scheme slug is required.")
    if not isinstance(changes, dict):
        raise AdminError("Update payload must be a dictionary.")

    df = _read_df()
    match = df[df["slug"].fillna("").astype(str).str.strip().str.lower() == target.lower()]
    if match.empty:
        raise AdminError(f"Scheme not found: {slug}")

    row_index = int(match.index[0])
    row = df.loc[row_index].copy()

    for key, value in changes.items():
        if key == "slug" or key not in CSV_COLUMNS:
            continue
        row[key] = _coerce(value)

    if not row["scheme_name"]:
        raise AdminError("scheme_name is required.")

    df.loc[row_index] = row
    _write_df(df)
    return row.to_dict()


def delete_scheme(slug: str):
    target = str(slug or "").strip()
    if not target:
        raise AdminError("Scheme slug is required.")

    df = _read_df()
    match = df[df["slug"].fillna("").astype(str).str.strip().str.lower() == target.lower()]
    if match.empty:
        raise AdminError(f"Scheme not found: {slug}")

    row_index = int(match.index[0])
    deleted_slug = str(df.loc[row_index, "slug"]).strip()
    df = df.drop(index=row_index).reset_index(drop=True)
    _write_df(df)
    return {"deleted": deleted_slug}


def save_uploaded_csv(filename: str, content: bytes | str):
    """Replace the whole scheme CSV. Everything is validated BEFORE the existing
    file is touched, so a bad upload can never destroy good data."""
    _ensure_data_dir()
    if not filename or not str(filename).lower().endswith(".csv"):
        raise AdminError("Please upload a CSV file.")

    payload = content if isinstance(content, bytes) else str(content).encode("utf-8")
    temp_path = DATA_DIR / "_uploaded_tmp.csv"
    temp_path.write_bytes(payload)
    try:
        df = pd.read_csv(temp_path, encoding="utf-8-sig")
    except Exception as exc:
        raise AdminError("Uploaded CSV could not be read as valid UTF-8 data.") from exc
    finally:
        temp_path.unlink(missing_ok=True)

    df.columns = [str(c).strip() for c in df.columns]
    if "scheme_name" not in df.columns:
        raise AdminError("The CSV must have a 'scheme_name' column.")

    normalized = _normalize_df(df)
    normalized = normalized[normalized["scheme_name"] != ""].reset_index(drop=True)
    if normalized.empty:
        raise AdminError("The CSV has no rows with a scheme_name, so there is nothing to import.")

    # Every row needs a unique slug (it is the record's identity in the dashboard).
    seen: set[str] = set()
    slugs = []
    for _, row in normalized.iterrows():
        base = _slugify(row["slug"] or row["scheme_name"])
        candidate, n = base, 2
        while candidate.lower() in seen:
            candidate = f"{base}-{n}"
            n += 1
        seen.add(candidate.lower())
        slugs.append(candidate)
    normalized["slug"] = slugs

    _write_df(normalized)
    return {"filename": filename, "rows": int(len(normalized))}


def save_uploaded_pdf(filename: str, content: bytes | str):
    _ensure_data_dir()
    # Keep only the final name: "../../x.pdf" and "C:\\a\\x.pdf" both become "x.pdf".
    safe_name = Path(str(filename or "").replace("\\", "/")).name
    if not safe_name or not safe_name.lower().endswith(".pdf"):
        raise AdminError("Please upload a PDF file.")

    payload = content if isinstance(content, bytes) else str(content).encode("utf-8")
    if not payload.lstrip().startswith(b"%PDF"):
        raise AdminError("That file does not look like a real PDF.")

    (DATA_DIR / safe_name).write_bytes(payload)
    return {"filename": safe_name, "saved": True}


def rebuild_search_index():
    """Rebuild the FAISS search index from the current CSV/PDF data."""
    try:
        import ingest
    except ImportError as exc:  # pragma: no cover
        raise AdminError("ingest.py is unavailable in this environment.") from exc

    docs = ingest.load_documents()
    chunks = ingest.split_documents(docs)
    ingest.build_index(chunks)
    return {"documents": len(docs), "chunks": len(chunks)}


__all__ = [
    "AdminError",
    "list_schemes",
    "get_scheme",
    "create_scheme",
    "update_scheme",
    "delete_scheme",
    "save_uploaded_csv",
    "save_uploaded_pdf",
    "rebuild_search_index",
]
