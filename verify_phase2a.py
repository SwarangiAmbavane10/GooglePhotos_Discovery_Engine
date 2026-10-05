"""
Verification script for Phase 2A results.
Inspects counts, samples, quotes, missing fields, and checks consistency.
"""
import pandas as pd
import sys

def verify():
    classified_df = pd.read_csv("Scrape_data/cleaned/retrieval_relevance_classified.csv")
    summary_df = pd.read_csv("Scrape_data/cleaned/retrieval_relevance_summary.csv")
    evidence_df = pd.read_csv("Scrape_data/cleaned/retrieval_evidence.csv")

    total = len(classified_df)
    hr = (classified_df["relevance_label"] == "highly_relevant").sum()
    pr = (classified_df["relevance_label"] == "possibly_relevant").sum()
    nr = (classified_df["relevance_label"] == "not_relevant").sum()

    print("=== SUMMARY METRICS ===")
    print(summary_df.to_string())

    print(f"\nTotal Records Processed: {total}")
    print(f"Highly Relevant: {hr} ({hr/total*100:.2f}%)")
    print(f"Possibly Relevant: {pr} ({pr/total*100:.2f}%)")
    print(f"Not Relevant: {nr} ({nr/total*100:.2f}%)")
    print(f"Sum check: {hr} + {pr} + {nr} = {hr + pr + nr} (Match 1035: {hr + pr + nr == 1035})")

    print("\n=== COUNT BY SOURCE ===")
    print(classified_df["source"].value_counts().to_string())

    print("\n=== CROSS-TAB (SOURCE x RELEVANCE LABEL) ===")
    ct = pd.crosstab(classified_df["source"], classified_df["relevance_label"], margins=True)
    print(ct.to_string())

    print("\n=== EVIDENCE QUOTE QUALITY CHECK ===")
    evidence_quotes_count = (evidence_df["evidence_quote"].fillna("").str.strip() != "").sum()
    print(f"Records with evidence quotes in retrieval_evidence.csv: {evidence_quotes_count} / {len(evidence_df)}")

    verbatim_mismatches = 0
    for idx, r in evidence_df.iterrows():
        q = str(r["evidence_quote"]).strip()
        t = str(r["text"]).strip()
        title = str(r["title"]).strip()
        full = f"{title} {t}"
        if q and q not in full and q not in t and q not in title:
            verbatim_mismatches += 1

    print(f"Verbatim quote mismatches: {verbatim_mismatches}")

    print("\n=== EXTRACTED FIELDS IN EVIDENCE DF ===")
    for col in [
        "relevance_label", "relevance_reason", "retrieval_scenario",
        "remembered_clues", "forgotten_or_unknown_clues", "search_behavior",
        "search_query_or_words_used", "failure_stage", "retrieval_barrier",
        "workaround", "retrieval_outcome", "evidence_quote", "evidence_strength"
    ]:
        populated = (evidence_df[col].fillna("").str.strip() != "").sum()
        missing = len(evidence_df) - populated
        print(f"  {col}: {populated} populated ({missing} blank/null)")

    print("\n=== SAMPLE HIGHLY RELEVANT RECORDS ===")
    for idx, r in evidence_df[evidence_df["relevance_label"] == "highly_relevant"].head(5).iterrows():
        print(f"[{r['source']}] {r['record_id']}:")
        print(f"  Quote: \"{r['evidence_quote']}\"")
        print(f"  Scenario: {r['retrieval_scenario']} | Clues: {r['remembered_clues']} | Behavior: {r['search_behavior']}")
        print(f"  Barrier: {r['retrieval_barrier']} | Workaround: {r['workaround']} | Outcome: {r['retrieval_outcome']}")
        print(f"  Reason: {r['relevance_reason']}\n")

if __name__ == "__main__":
    verify()
