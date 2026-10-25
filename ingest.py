

import os
import pandas as pd
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

DATA_DIR = "data"
INDEX_DIR = "faiss_index"
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  

CSV_TEXT_COLUMNS = ["schemeCategory", "tags", "details", "benefits", "eligibility", "application", "documents"]
CSV_NAME_COLUMN = "scheme_name"
CSV_SLUG_COLUMN = "slug"


def load_pdf_documents():
    """Load every PDF in DATA_DIR. Each page becomes a LangChain Document
    with metadata like {'source': 'pm_kisan.pdf', 'page': 2}."""
    docs = []
    pdf_files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(".pdf")]

    for filename in pdf_files:
        path = os.path.join(DATA_DIR, filename)
        print(f"Loading {filename} ...")
        loader = PyPDFLoader(path)
        pages = loader.load()
        for page in pages:
            page.metadata["source"] = filename
        docs.extend(pages)

    if pdf_files:
        print(f"Loaded {len(docs)} pages from {len(pdf_files)} PDF(s).")
    return docs


def load_csv_documents():
    """Load every CSV in DATA_DIR. Each ROW becomes one LangChain Document
    (one scheme = one document), with metadata like
    {'source': 'PM-KISAN', 'row': 12, 'file': 'updated_data.csv'}.

    This is built for the 'Indian Government Schemes' Kaggle CSV format
    (scheme_name, slug, details, benefits, eligibility, application,
    documents, level, schemeCategory, tags). If your CSV has different
    column names, update CSV_TEXT_COLUMNS / CSV_NAME_COLUMN above.
    """
    docs = []
    csv_files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith(".csv")]

    for filename in csv_files:
        path = os.path.join(DATA_DIR, filename)
        print(f"Loading {filename} ...")
        df = pd.read_csv(path)

        missing = [c for c in [CSV_NAME_COLUMN, *CSV_TEXT_COLUMNS] if c not in df.columns]
        if missing:
            print(f"  [warning] columns not found in {filename}, skipping them: {missing}")

        name_col = CSV_NAME_COLUMN if CSV_NAME_COLUMN in df.columns else df.columns[0]
        text_cols = [c for c in CSV_TEXT_COLUMNS if c in df.columns]

        for i, row in df.iterrows():
            scheme_name = str(row.get(name_col, f"row_{i}")).strip()

            # Combine the useful text fields into one readable block per scheme.
            parts = [f"Scheme Name: {scheme_name}"]
            for col in text_cols:
                value = row.get(col)
                if pd.notna(value) and str(value).strip():
                    parts.append(f"{col.capitalize()}: {value}")
            content = "\n\n".join(parts)

            if not content.strip():
                continue  # skip rows with no usable text

            # Keep stable identifiers in metadata.  The chat app uses these to
            # recognise a scheme named in a question (for example, "PM-KISAN")
            # and restrict retrieval to that scheme instead of a document that
            # happens to mention it.
            slug = str(row.get(CSV_SLUG_COLUMN, "")).strip()
            docs.append(Document(
                page_content=content,
                metadata={
                    "source": scheme_name,
                    "scheme_name": scheme_name,
                    "slug": slug,
                    "row": int(i),
                    "file": filename,
                    "page": "N/A",
                },
            ))

    if csv_files:
        print(f"Loaded {len(docs)} scheme rows from {len(csv_files)} CSV file(s).")
    return docs


def load_documents():
    """Load every PDF and CSV in DATA_DIR and combine them into one list
    of documents ready for chunking."""
    if not os.path.isdir(DATA_DIR):
        raise FileNotFoundError(
            f"'{DATA_DIR}/' not found. Create it and drop your scheme PDFs/CSVs inside."
        )

    docs = load_pdf_documents() + load_csv_documents()

    if not docs:
        raise FileNotFoundError(
            f"No PDFs or CSVs found in '{DATA_DIR}/'. Add at least one and re-run."
        )

    return docs


def split_documents(docs):
    """Break long pages into smaller overlapping chunks so retrieval
    can find precise, relevant passages instead of whole pages."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(docs)
    print(f"Split into {len(chunks)} chunks.")
    return chunks


def build_index(chunks):
    """Embed all chunks and save a FAISS index to disk."""
    print(f"Loading embedding model: {EMBEDDING_MODEL} (first run downloads it, be patient)...")
    embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)

    print("Embedding chunks and building FAISS index...")
    vectorstore = FAISS.from_documents(chunks, embeddings)

    os.makedirs(INDEX_DIR, exist_ok=True)
    vectorstore.save_local(INDEX_DIR)
    print(f"Saved FAISS index to '{INDEX_DIR}/'.")


if __name__ == "__main__":
    documents = load_documents()
    chunks = split_documents(documents)
    build_index(chunks)
    print("\nDone. You can now run: python rag_chat.py")
