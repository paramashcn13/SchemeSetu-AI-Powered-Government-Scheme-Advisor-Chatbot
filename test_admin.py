"""
Standalone test for admin.py's CRUD logic. Run from your project root
(same folder as app.py, admin.py). Creates a throwaway test scheme,
updates it, lists/searches for it, then deletes it -- the CSV should end
up with the exact same row count it started with.

Does NOT test rebuild_search_index() (that's slow -- re-embeds everything
-- and genuinely rebuilds faiss_index/ on disk, so it's left for a manual
check via the API instead of running on every test pass).

Run: python test_admin.py
"""

import admin


def main():
    before = admin.list_schemes(page_size=1)
    baseline_total = before["total"]
    print(f"Starting row count: {baseline_total}")

    # ---- CREATE ----
    print("\n--- CREATE ---")
    new_scheme = admin.create_scheme({
        "scheme_name": "Test Scheme For Admin Dashboard QA",
        "details": "This is a throwaway row created by test_admin.py.",
        "eligibility": "Anyone running this test script.",
        "benefits": "Confidence that CRUD works.",
        "level": "Central",
        "schemeCategory": "Testing",
        "tags": "test, qa",
    })
    slug = new_scheme["slug"]
    print(f"Created scheme with slug: {slug}")
    assert slug, "create_scheme should auto-generate a slug"

    after_create = admin.list_schemes(page_size=1)
    assert after_create["total"] == baseline_total + 1, "row count should go up by 1"
    print("Row count after create: OK (+1)")

    # ---- READ (single) ----
    print("\n--- READ ---")
    fetched = admin.get_scheme(slug)
    assert fetched["scheme_name"] == "Test Scheme For Admin Dashboard QA"
    print(f"Fetched scheme by slug: {fetched['scheme_name']}")

    # ---- READ (search) ----
    search_results = admin.list_schemes(search="Admin Dashboard QA")
    assert search_results["total"] == 1, "search should find exactly the test row"
    print("Search found the test row: OK")

    # ---- UPDATE ----
    print("\n--- UPDATE ---")
    updated = admin.update_scheme(slug, {"benefits": "Updated benefits text."})
    assert updated["benefits"] == "Updated benefits text."
    print(f"Updated benefits field: {updated['benefits']}")

    # confirm the slug itself can't be changed via update (identifier safety)
    updated_again = admin.update_scheme(slug, {"slug": "should-not-change", "details": "x"})
    assert updated_again["slug"] == slug, "slug must not change via update_scheme"
    print("Confirmed slug is immutable via update: OK")

    # ---- DELETE ----
    print("\n--- DELETE ---")
    result = admin.delete_scheme(slug)
    assert result["deleted"] == slug
    print(f"Deleted scheme: {slug}")

    after_delete = admin.list_schemes(page_size=1)
    assert after_delete["total"] == baseline_total, "row count should return to baseline"
    print(f"Row count back to baseline ({baseline_total}): OK")

    # ---- ERROR HANDLING ----
    print("\n--- ERROR HANDLING ---")
    try:
        admin.get_scheme("this-slug-does-not-exist")
        print("FAIL: should have raised AdminError")
    except admin.AdminError:
        print("get_scheme on missing slug raises AdminError: OK")

    try:
        admin.create_scheme({"details": "missing scheme_name"})
        print("FAIL: should have raised AdminError")
    except admin.AdminError:
        print("create_scheme without scheme_name raises AdminError: OK")

    try:
        admin.delete_scheme("this-slug-does-not-exist")
        print("FAIL: should have raised AdminError")
    except admin.AdminError:
        print("delete_scheme on missing slug raises AdminError: OK")

    print("\nAll checks passed. CSV is back to its original row count.")


if __name__ == "__main__":
    main()