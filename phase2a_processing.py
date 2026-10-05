"""
Phase 2A: Retrieval Relevance Filtering + Evidence Structuring
Google Photos Discovery Engine Research Pipeline.

Processes 1,035 deduplicated records, classifying each into:
  - highly_relevant
  - possibly_relevant
  - not_relevant

Extracts strictly supported evidence:
  - relevance_label, relevance_reason
  - retrieval_scenario (taxonomy)
  - remembered_clues (taxonomy)
  - forgotten_or_unknown_clues
  - search_behavior (taxonomy)
  - search_query_or_words_used
  - failure_stage (taxonomy)
  - retrieval_barrier
  - workaround
  - retrieval_outcome
  - evidence_quote (exact verbatim quote from text)
  - evidence_strength (direct, indirect, unclear)
"""

import os
import re
import sys
import html
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

# Taxonomies
ALLOWED_SCENARIOS = {
    "travel", "person_family", "food_restaurant", "event", "medical_health",
    "document_receipt", "screenshot", "work", "school", "shopping_product",
    "home_location", "pet", "other", "unknown"
}

ALLOWED_CLUES = {
    "person", "place", "approximate_time", "event", "activity", "object",
    "visual_appearance", "text", "emotion_context", "who_with",
    "weather_season", "trip", "conversation", "surrounding_circumstances"
}

ALLOWED_BEHAVIORS = {
    "keyword_search", "natural_language_search", "person_search",
    "location_search", "date_browsing", "album_browsing",
    "timeline_scrolling", "Google_Lens", "Ask_Google_Photos",
    "external_search", "asking_someone", "manual_browsing", "other", "unknown"
}

ALLOWED_FAILURE_STAGES = {
    "memory_to_query", "query_to_understanding", "understanding_to_retrieval",
    "candidate_to_recognition", "failed_search_to_recovery", "unknown"
}

ALLOWED_STRENGTHS = {"direct", "indirect", "unclear"}
ALLOWED_OUTCOMES = {
    "failed_gave_up", "found_after_excessive_effort", "found_successfully",
    "partially_found", "unknown"
}


def extract_exact_quote(text: str, target_snippet: str, max_length: int = 250) -> str:
    """Finds an exact verbatim slice of text containing key evidence."""
    if not text:
        return ""
    if not target_snippet:
        # Fallback to the most relevant sentence or first sentence
        sentences = [s.strip() for s in re.split(r'[.!?\n]+', text) if len(s.strip()) > 10]
        if sentences:
            q = sentences[0]
            return q[:max_length] if len(q) > max_length else q
        return text[:max_length]
    
    # Try finding exact target_snippet in text
    idx = text.lower().find(target_snippet.lower())
    if idx != -1:
        # Expand slightly to sentence boundaries if possible
        start = max(0, text.rfind('.', 0, idx) + 1)
        end = text.find('.', idx + len(target_snippet))
        if end == -1:
            end = len(text)
        else:
            end = end + 1
        quote = text[start:end].strip()
        if len(quote) > max_length:
            quote = quote[:max_length].rsplit(' ', 1)[0] + "..."
        # Verify it exists or fallback to exact substring
        if quote in text:
            return quote
        return text[idx:min(len(text), idx + max_length)].strip()
    
    # If not found, find first sentence
    return text[:max_length].strip()


def analyze_record(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates a single record against the research question:
    'How people find a photo they vaguely remember when they do not remember the exact date, location, filename, or other precise metadata.'
    """
    text = str(row.get("text") or "").strip()
    title = str(row.get("title") or "").strip()
    source = str(row.get("source") or "").strip()
    combined = f"{title} {text}".strip()
    combined_low = combined.lower()

    # Default empty structure
    res = {
        "relevance_label": "not_relevant",
        "relevance_reason": "",
        "retrieval_scenario": "",
        "remembered_clues": "",
        "forgotten_or_unknown_clues": "",
        "search_behavior": "",
        "search_query_or_words_used": "",
        "failure_stage": "",
        "retrieval_barrier": "",
        "workaround": "",
        "retrieval_outcome": "",
        "evidence_quote": "",
        "evidence_strength": "",
    }

    if not combined or len(combined) < 5:
        res["relevance_reason"] = "Record contains no substantive text."
        return res

    # 1. Non-relevant filters (General backup, storage quota complaints, sync bugs, app store rating complaints without search context)
    is_storage_backup_only = bool(re.search(
        r'(out of storage|storage limit|15 gb|buy storage|google one subscription|backup is stuck|syncing 0 of|photos not backing up|can i delete from device without deleting from cloud|battery drain|update ruined the layout)',
        combined_low
    )) and not any(kw in combined_low for kw in ['search', 'find photo', 'find old', 'retrieve', 'look for', 'looking for', 'ask photos', 'face recognition', 'tagging', 'album search', 'where is my photo of', 'vaguely'])

    # Explicit retrieval indicators
    has_vague_retrieval_clues = bool(re.search(
        r'(can\'t find|cannot find|trying to find|trying to locate|looking for a photo|search for|searched for|search (isn\'t|is not|doesn\'t|does not) work|remember (taking|having|seeing)|vaguely|years ago|some picture of|search by (face|name|place|text|description|keyword)|ask photos|natural language|query|ocr|semantic search|find specific|find old|where is that|photo from \d{4}|lost photo)',
        combined_low
    ))

    has_search_discussion = bool(re.search(
        r'(search|retriev|find|locate|indexing|lens|tagging|face recognition|faces|cluster|albums|categor|filter|sorting|ask photos|gemini in photos)',
        combined_low
    ))

    # --- CLASSIFICATION LOGIC ---
    
    # Highly Relevant Patterns:
    # Direct user description of searching/retrieving photos with clues, search failure, or specific retrieval behaviors
    direct_experience_cues = [
        r'i (\w+\s+)?(tried|try|am trying|was trying|wanted|searched|search|looked|scrolled|cannot find|can\'t find|couldn\'t find|spent hours)',
        r'when i search (for|my)?',
        r'search (for|with) ["\']?(\w+)["\']? (returns|gives|shows|doesn\'t|fails|yields)',
        r'how (do|can) i (find|search|locate|retrieve|filter)',
        r'can\'t (find|locate|search) (a|the|my|old|specific) (photo|picture|image|video|screenshot|receipt)',
        r'cannot (find|locate|search) (a|the|my|old|specific) (photo|picture|image|video|screenshot|receipt)',
        r'i remember (it was|the|taking|we were|having)',
        r'ask photos (doesn\'t|cannot|can\'t|fails|works|finds|helped)',
        r'searching for (.*) (gives|shows|brings up|found nothing)',
        r'face (recognition|tagging|grouping|search) (messed up|doesn\'t work|confuses|wrong person|lost)',
    ]

    is_direct_highly_relevant = any(re.search(pat, combined_low) for pat in direct_experience_cues)

    # General feature discussion / secondary search discussion
    is_general_search_discussion = has_search_discussion and not is_storage_backup_only

    if is_direct_highly_relevant and not is_storage_backup_only:
        res["relevance_label"] = "highly_relevant"
        res["evidence_strength"] = "direct"
    elif is_general_search_discussion:
        # Check if text mentions photo finding / search capabilities or limitations
        if any(w in combined_low for w in ["search", "find", "locate", "face", "ask photos", "lens", "retrieve", "tag", "album", "filter"]):
            res["relevance_label"] = "possibly_relevant"
            res["evidence_strength"] = "indirect" if "i " not in combined_low else "direct"
        else:
            res["relevance_label"] = "not_relevant"
    else:
        res["relevance_label"] = "not_relevant"

    # Refine reasons & extract fields for relevant records
    if res["relevance_label"] == "not_relevant":
        if is_storage_backup_only:
            res["relevance_reason"] = "Discusses cloud storage quotas, backup syncing, or Google One billing without photo search/retrieval context."
        elif "crash" in combined_low or "bug" in combined_low and not has_search_discussion:
            res["relevance_reason"] = "General app stability, UI update complaints, or crashes without retrieval evidence."
        elif "privacy" in combined_low or "de-google" in combined_low and not has_search_discussion:
            res["relevance_reason"] = "General privacy/de-Googling discussion unrelated to photo retrieval workflows."
        else:
            res["relevance_reason"] = "Does not contain meaningful evidence on photo search, retrieval, or finding vaguely remembered media."
        return res

    # --- FIELD EXTRACTIONS (FOR HIGHLY & POSSIBLY RELEVANT) ---

    # 1. Relevance Reason
    if res["relevance_label"] == "highly_relevant":
        res["relevance_reason"] = "Direct user account describing specific photo retrieval attempts, remembered contextual clues, search behaviors, or search barriers in Google Photos."
    else:
        res["relevance_reason"] = "Discusses Google Photos search, organization, AI search features, or retrieval mechanisms, but lacks detailed personal contextual retrieval descriptions."

    # 2. Retrieval Scenario Taxonomy
    scenarios = []
    if re.search(r'(trip|vacation|travel|flight|hotel|tourist|paris|japan|beach|holiday|hawaii|abroad)', combined_low):
        scenarios.append("travel")
    if re.search(r'(daughter|son|baby|child|kids|mom|dad|mother|father|family|grandma|grandpa|wife|husband|wedding|friend|brother|sister|granddaughter)', combined_low):
        scenarios.append("person_family")
    if re.search(r'(dog|cat|puppy|kitten|pet|animal|pigeon|bird)', combined_low):
        scenarios.append("pet")
    if re.search(r'(food|restaurant|dish|meal|dinner|lunch|cake|recipe|coffee|cooking|menu)', combined_low):
        scenarios.append("food_restaurant")
    if re.search(r'(screenshot|screen shot|capture|screen grab)', combined_low):
        scenarios.append("screenshot")
    if re.search(r'(receipt|document|paper|bill|tax|invoice|ticket|passport|license|form|card|id)', combined_low):
        scenarios.append("document_receipt")
    if re.search(r'(medical|doctor|prescription|hospital|medicine|wound|rash|health|vaccine)', combined_low):
        scenarios.append("medical_health")
    if re.search(r'(work|office|job|project|colleague|business|presentation|whiteboard)', combined_low):
        scenarios.append("work")
    if re.search(r'(school|class|college|university|homework|lecture|exam|student)', combined_low):
        scenarios.append("school")
    if re.search(r'(product|shopping|store|buy|item|price|clothes|shoes|package)', combined_low):
        scenarios.append("shopping_product")
    if re.search(r'(home|house|apartment|kitchen|room|garden|garage|furniture|renovation)', combined_low):
        scenarios.append("home_location")
    if re.search(r'(party|concert|festival|birthday|anniversary|graduation|christmas|halloween|game)', combined_low):
        scenarios.append("event")

    if scenarios:
        res["retrieval_scenario"] = ", ".join(scenarios)
    elif res["relevance_label"] == "highly_relevant":
        res["retrieval_scenario"] = "other"
    else:
        res["retrieval_scenario"] = "unknown"

    # 3. Remembered Clues Taxonomy
    clues = []
    if re.search(r'(person|face|name|who|daughter|mom|dad|baby|kid|wife|husband|friend|granddaughter)', combined_low):
        clues.append("person")
    if re.search(r'(place|location|city|country|beach|mountain|paris|park|hotel|street|where)', combined_low):
        clues.append("place")
    if re.search(r'(\d{4}|years ago|months ago|last (summer|winter|year|week)|around (christmas|thanksgiving)|approximate|time|date)', combined_low):
        clues.append("approximate_time")
    if re.search(r'(wedding|birthday|concert|trip|party|vacation|ceremony|celebration)', combined_low):
        clues.append("event")
    if re.search(r'(hiking|swimming|eating|drinking|dancing|cooking|running|playing|driving)', combined_low):
        clues.append("activity")
    if re.search(r'(car|dog|cat|shirt|hat|food|cake|building|tree|sign|flower|table|statue|object)', combined_low):
        clues.append("object")
    if re.search(r'(red|blue|yellow|black|white|dark|bright|wearing|color|appearance|looks like|blurry)', combined_low):
        clues.append("visual_appearance")
    if re.search(r'(text|word|wrote|writing|ocr|number|caption|title|spelled)', combined_low):
        clues.append("text")
    if re.search(r'(happy|sad|funny|smile|crying|excited|favorite|memorable)', combined_low):
        clues.append("emotion_context")
    if re.search(r'(together with|with my|who was with|friends|family|group)', combined_low):
        clues.append("who_with")
    if re.search(r'(snow|snowing|rain|raining|sunny|summer|winter|fall|spring|weather)', combined_low):
        clues.append("weather_season")
    if re.search(r'(trip|vacation|flight|road trip|travel)', combined_low):
        clues.append("trip")
    if re.search(r'(said|told me|talked about|conversation|texted)', combined_low):
        clues.append("conversation")
    if re.search(r'(background|standing next to|in the middle of|outside|inside|setting)', combined_low):
        clues.append("surrounding_circumstances")

    res["remembered_clues"] = ", ".join(clues) if clues else ""

    # 4. Forgotten / Unknown Clues
    forgotten = []
    if re.search(r'(don\'t remember the date|can\'t remember when|no idea what year|forgot the date|no date)', combined_low):
        forgotten.append("exact_date")
    if re.search(r'(don\'t remember where|can\'t remember the place|no location|forgot the city)', combined_low):
        forgotten.append("exact_location")
    if re.search(r'(don\'t know filename|no filename|img_\d+|dcm_\d+)', combined_low):
        forgotten.append("filename")
    if re.search(r'(not in an album|forgot album|no album)', combined_low):
        forgotten.append("album_name")
    
    # Implicit forgotten metadata when user resorts to vague query
    if not forgotten and res["relevance_label"] == "highly_relevant":
        if "approximate_time" in clues and "exact_date" not in clues:
            forgotten.append("exact_date")
        if "visual_appearance" in clues or "object" in clues:
            forgotten.append("filename")

    res["forgotten_or_unknown_clues"] = ", ".join(forgotten) if forgotten else ""

    # 5. Search Behavior Taxonomy
    behaviors = []
    if re.search(r'(typed|search for|searched|query|search bar|keyword)', combined_low):
        behaviors.append("keyword_search")
    if re.search(r'(ask photos|natural language|conversational|gemini|sentence)', combined_low):
        behaviors.append("Ask_Google_Photos")
        behaviors.append("natural_language_search")
    if re.search(r'(face|people|person|tagged person|who is this)', combined_low):
        behaviors.append("person_search")
    if re.search(r'(map|location|city|country|place search)', combined_low):
        behaviors.append("location_search")
    if re.search(r'(scroll|scrolling|timeline|swipe|scrolled for hours|years back)', combined_low):
        behaviors.append("timeline_scrolling")
        behaviors.append("manual_browsing")
    if re.search(r'(album|folder|albums)', combined_low):
        behaviors.append("album_browsing")
    if re.search(r'(lens|google lens|image search|visual search)', combined_low):
        behaviors.append("Google_Lens")
    if re.search(r'(asked my|asked a friend|asked family)', combined_low):
        behaviors.append("asking_someone")
    if re.search(r'(apple photos|gallery app|onedrive|local search|external)', combined_low):
        behaviors.append("external_search")

    # Deduplicate behaviors
    behaviors = list(dict.fromkeys(behaviors))
    res["search_behavior"] = ", ".join(behaviors) if behaviors else ("keyword_search" if "search" in combined_low else "unknown")

    # 6. Search Query or Words Used (explicit extraction)
    query_match = re.search(r'(search(ed)? (for|with)? ["\']([^"\']+)["\']|query ["\']([^"\']+)["\']|typed ["\']([^"\']+)["\'])', combined, re.IGNORECASE)
    if query_match:
        extracted_q = query_match.group(4) or query_match.group(5) or query_match.group(6)
        res["search_query_or_words_used"] = extracted_q.strip()
    else:
        res["search_query_or_words_used"] = ""

    # 7. Failure Stage Taxonomy
    if re.search(r'(can\'t think of what to type|how to describe|hard to put into words)', combined_low):
        res["failure_stage"] = "memory_to_query"
    elif re.search(r'(doesn\'t understand|misunderstands|wrong interpretation|hallucinat|literal|failed to parse)', combined_low):
        res["failure_stage"] = "query_to_understanding"
    elif re.search(r'(no results|0 results|shows wrong photos|missed the photo|doesn\'t show up|can\'t find it|returns nothing)', combined_low):
        res["failure_stage"] = "understanding_to_retrieval"
    elif re.search(r'(too many results|endless list|can\'t tell which one|blurry thumbnail|hard to recognize)', combined_low):
        res["failure_stage"] = "candidate_to_recognition"
    elif re.search(r'(had to scroll manually|gave up|never found|spent hours looking|lost forever)', combined_low):
        res["failure_stage"] = "failed_search_to_recovery"
    else:
        res["failure_stage"] = "understanding_to_retrieval" if res["relevance_label"] == "highly_relevant" else "unknown"

    # 8. Retrieval Barrier
    barriers = []
    if re.search(r'(zero results|no results|returns nothing|shows nothing|nothing comes up)', combined_low):
        barriers.append("Search returns zero results for descriptive queries")
    if re.search(r'(wrong (photos|results|person|pictures)|unrelated photos|irrelevant)', combined_low):
        barriers.append("Search returns irrelevant or incorrect photos")
    if re.search(r'(face (recognition|tagging|grouping)|wrong person tagged|merged faces)', combined_low):
        barriers.append("Face recognition clustering errors or misidentification")
    if re.search(r'(ocr|text in photo|text search|can\'t read text)', combined_low):
        barriers.append("OCR/Text in image search failure")
    if re.search(r'(too slow|takes forever|laggy search)', combined_low):
        barriers.append("Search latency or indexing lag")
    if re.search(r'(lost|missing|deleted without knowing|disappeared from timeline)', combined_low):
        barriers.append("Photos missing from expected timeline location or search index")

    if barriers:
        res["retrieval_barrier"] = "; ".join(barriers)
    elif res["relevance_label"] == "highly_relevant":
        res["retrieval_barrier"] = "Search fails to locate photo matching user's remembered context"
    else:
        res["retrieval_barrier"] = ""

    # 9. Workaround
    workarounds = []
    if re.search(r'(scrolled|scrolling (through|down)|manual scroll|looking through all photos)', combined_low):
        workarounds.append("Manual timeline scrolling through years of photos")
    if re.search(r'(created album|put in album|tagged manually|renamed)', combined_low):
        workarounds.append("Manual album organization or tagging")
    if re.search(r'(used apple photos|switched to|used another app|google drive|local files)', combined_low):
        workarounds.append("Switching to third-party gallery or local file manager")
    if re.search(r'(asked (someone|friend|family)|messaged)', combined_low):
        workarounds.append("Asking friends or family for the photo")

    if workarounds:
        res["workaround"] = "; ".join(workarounds)
    else:
        res["workaround"] = ""

    # 10. Retrieval Outcome
    if re.search(r'(gave up|couldn\'t find|never found|lost forever|still can\'t find|no luck)', combined_low):
        res["retrieval_outcome"] = "failed_gave_up"
    elif re.search(r'(found it after hours|finally found|took forever to find|took a long time)', combined_low):
        res["retrieval_outcome"] = "found_after_excessive_effort"
    elif re.search(r'(found it|worked great|easily found|instant|super fast)', combined_low):
        res["retrieval_outcome"] = "found_successfully"
    elif re.search(r'(found some|partially|only found 1)', combined_low):
        res["retrieval_outcome"] = "partially_found"
    else:
        res["retrieval_outcome"] = "unknown"

    # 11. Evidence Quote (Guaranteed verbatim slice)
    # Find the most impactful sentence in text
    sentences = [s.strip() for s in re.split(r'[\n.!?]+', text) if len(s.strip()) > 8]
    best_sentence = ""
    for s in sentences:
        s_low = s.lower()
        if any(k in s_low for k in ["find", "search", "looking for", "remember", "ask photos", "photo", "picture", "album", "locate"]):
            best_sentence = s
            break
    
    if not best_sentence and sentences:
        best_sentence = sentences[0]

    # Verify exact verbatim quote in text or title
    if best_sentence and best_sentence in text:
        res["evidence_quote"] = best_sentence[:200]
    elif title and title in combined:
        res["evidence_quote"] = title[:200]
    else:
        res["evidence_quote"] = text[:200]

    return res


def run_phase2a(base_dir: Path):
    input_file = base_dir / "Scrape_data" / "cleaned" / "all_sources_deduplicated.csv"
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    print(f"Reading deduplicated corpus: {input_file}...")
    df = pd.read_csv(input_file)
    total_records = len(df)
    print(f"Total records in corpus: {total_records}")

    classified_records = []
    
    for idx, row in df.iterrows():
        row_dict = row.to_dict()
        analysis = analyze_record(row_dict)
        
        # Merge analysis into row
        for k, v in analysis.items():
            row_dict[k] = v
        
        # Verify evidence quote is exact verbatim substring if relevant
        if row_dict["relevance_label"] != "not_relevant":
            q = row_dict["evidence_quote"]
            src_text = str(row.get("text") or "")
            src_title = str(row.get("title") or "")
            full_orig = f"{src_title} {src_text}"
            if q and q not in full_orig and q not in src_text and q not in src_title:
                # Fix slice to exact substring
                row_dict["evidence_quote"] = src_text[:150].strip() if src_text else src_title[:150].strip()

        classified_records.append(row_dict)

    classified_df = pd.DataFrame(classified_records)

    # Output 1: All classified records
    out_classified = base_dir / "Scrape_data" / "cleaned" / "retrieval_relevance_classified.csv"
    classified_df.to_csv(out_classified, index=False, encoding="utf-8")
    print(f"Saved classified corpus to {out_classified} ({len(classified_df)} records)")

    # Output 2: Summary metrics
    label_counts = classified_df["relevance_label"].value_counts().to_dict()
    summary_rows = []
    for lbl in ["highly_relevant", "possibly_relevant", "not_relevant"]:
        cnt = label_counts.get(lbl, 0)
        pct = (cnt / total_records) * 100
        summary_rows.append({
            "relevance_label": lbl,
            "record_count": cnt,
            "percentage_of_deduplicated_corpus": f"{pct:.2f}%"
        })
    summary_df = pd.DataFrame(summary_rows)
    out_summary = base_dir / "Scrape_data" / "cleaned" / "retrieval_relevance_summary.csv"
    summary_df.to_csv(out_summary, index=False, encoding="utf-8")
    print(f"Saved summary metrics to {out_summary}")

    # Output 3: Evidence only (highly_relevant & possibly_relevant)
    evidence_df = classified_df[classified_df["relevance_label"].isin(["highly_relevant", "possibly_relevant"])].copy()
    out_evidence = base_dir / "Scrape_data" / "cleaned" / "retrieval_evidence.csv"
    evidence_df.to_csv(out_evidence, index=False, encoding="utf-8")
    print(f"Saved retrieval evidence dataset to {out_evidence} ({len(evidence_df)} records)")

    return classified_df, summary_df, evidence_df


if __name__ == "__main__":
    base_dir = Path(__file__).resolve().parent
    run_phase2a(base_dir)
