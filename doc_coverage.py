"""
doc_coverage.py -- run once against your real CSV to see how well the document
vocabulary (eligibility.DOCUMENT_KEYWORDS) fits your data:

    python doc_coverage.py

Prints how many schemes name at least one known document, how often each
document appears, and the most common comma/'and'-separated items in the
`documents` column that match NOTHING -- those are the candidates to add to
DOCUMENT_KEYWORDS (or to a new key).
"""
import re
from collections import Counter

import eligibility

df = eligibility.load_dataframe(force_reload=True)
total = len(df)
known = int((df["_documents"].map(len) > 0).sum())
blank = int((df["documents"].str.strip() == "").sum())
print(f"{total} schemes | {known} name a known document ({known / total:.0%}) | {blank} have an empty documents column\n")

counts = Counter(d for docs in df["_documents"] for d in docs)
for key, n in counts.most_common():
    print(f"  {eligibility.DOCUMENT_LABELS[key]:<34} {n:>5}")

unmatched = Counter()
for text in df["documents"]:
    for item in re.split(r"[,;\n\u2022]|\band\b|\bor\b", text):
        item = re.sub(r"\s+", " ", item).strip(" .-:").lower()
        if 3 < len(item) < 60 and not eligibility._extract_documents(item):
            unmatched[item] += 1

print("\nMost common items that matched no known document (add the useful ones):")
for item, n in unmatched.most_common(25):
    print(f"  {n:>5}  {item}")
