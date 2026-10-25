"""
Quick standalone test for eligibility.py — run this from your project root
(same folder as app.py, rag_chat.py, eligibility.py) BEFORE wiring it into
the FastAPI app, to confirm it works against your actual data/ CSV.

Run: python test_eligibility.py
"""

import time
import eligibility


def show(label, result):
    print(f"\n{'='*60}")
    print(label)
    print(f"{'='*60}")
    print(f"Total matched: {result['total_matched']} | Showing: {result['returned']}")
    for m in result["matches"][:8]:
        print(f"  - {m['scheme_name']}  [{m['level']}]")
        if m["eligibility_snippet"]:
            print(f"      eligibility: {m['eligibility_snippet'][:120]}...")


def main():
    print("Loading and precomputing dataframe (one-time cost)...")
    t0 = time.time()
    eligibility.load_dataframe()
    print(f"Done in {time.time() - t0:.2f}s")

    # Test 1: no filters at all -- should return a large chunk of the dataset
    t0 = time.time()
    result = eligibility.filter_schemes()
    show("TEST 1: No filters (should match most/all schemes)", result)
    print(f"Query time: {time.time() - t0:.3f}s")

    # Test 2: category only
    t0 = time.time()
    result = eligibility.filter_schemes(category="farmer")
    show("TEST 2: category=farmer", result)
    print(f"Query time: {time.time() - t0:.3f}s")

    # Test 3: category + state
    t0 = time.time()
    result = eligibility.filter_schemes(category="student", state="Tamil Nadu")
    show("TEST 3: category=student, state=Tamil Nadu", result)
    print(f"Query time: {time.time() - t0:.3f}s")

    # Test 4: full profile
    t0 = time.time()
    result = eligibility.filter_schemes(
        age=45, income=150000, state="Maharashtra", category="farmer"
    )
    show("TEST 4: age=45, income=150000, state=Maharashtra, category=farmer", result)
    print(f"Query time: {time.time() - t0:.3f}s")

    # Test 5: a narrow/unlikely combo -- should return few or zero, and that's OK
    t0 = time.time()
    result = eligibility.filter_schemes(
        age=22, income=50000, state="Sikkim", category="person_with_disability"
    )
    show("TEST 5: narrow combo (few/zero matches is fine here)", result)
    print(f"Query time: {time.time() - t0:.3f}s")

    print("\n\nAll tests ran without errors. Eyeball the results above:")
    print("- Do scheme names roughly make sense for each filter combo?")
    print("- Are State-level schemes in Test 3 actually Tamil Nadu (or Central)?")
    print("- Query time should be well under 1 second per test after the initial load.")


if __name__ == "__main__":
    main()