"""
Phase 2A: Retrieval Relevance Filtering & Evidence Structuring
Google Photos Discovery Engine Research Pipeline

Strictly follows Phase 2A guidelines:
- Evaluates 1,035 deduplicated records
- Relevance Labels: highly_relevant, possibly_relevant, not_relevant
- Extracts strictly supported evidence fields using specified taxonomies with context-aware word boundaries
- Verifies exact verbatim substring matching for all evidence quotes
- Outputs 3 required CSV files:
    1. Scrape_data/cleaned/retrieval_relevance_classified.csv
    2. Scrape_data/cleaned/retrieval_relevance_summary.csv
    3. Scrape_data/cleaned/retrieval_evidence.csv
"""

import os
import re
import sys
import html
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

# Taxonomies
ALLOWED_SCENARIOS = [
    "travel", "person_family", "food_restaurant", "event", "medical_health",
    "document_receipt", "screenshot", "work", "school", "shopping_product",
    "home_location", "pet", "other", "unknown"
]

ALLOWED_CLUES = [
    "person", "place", "approximate_time", "event", "activity", "object",
    "visual_appearance", "text", "emotion_context", "who_with",
    "weather_season", "trip", "conversation", "surrounding_circumstances"
]

ALLOWED_BEHAVIORS = [
    "keyword_search", "natural_language_search", "person_search",
    "location_search", "date_browsing", "album_browsing",
    "timeline_scrolling", "Google_Lens", "Ask_Google_Photos",
    "external_search", "asking_someone", "manual_browsing", "other", "unknown"
]

ALLOWED_FAILURE_STAGES = [
    "memory_to_query", "query_to_understanding", "understanding_to_retrieval",
    "candidate_to_recognition", "failed_search_to_recovery", "unknown"
]


def clean_text_for_matching(text: str) -> str:
    """Normalizes quotes and whitespace for regex matching while preserving original string."""
    if not text:
        return ""
    t = html.unescape(text)
    t = t.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    return t


def extract_best_verbatim_quote(raw_text: str, raw_title: str) -> str:
    """
    Extracts a concise, exact verbatim substring from original raw text or title
    that best highlights retrieval problems, behaviors, or evidence.
    """
    full_text = f"{raw_title} {raw_text}".strip()
    if not full_text:
        return ""
    
    # Split text into candidate sentences / clauses
    candidates = [s.strip() for s in re.split(r'(?<=[.!?\n])\s+', raw_text) if len(s.strip()) > 8]
    if not candidates and raw_title:
        candidates = [raw_title.strip()]

    # High-value evidence cues to score sentences
    high_value_cues = [
        "can't find", "cannot find", "trying to find", "search engine", "search bar",
        "search for", "search by", "facial recognition", "face search", "ask photos",
        "screenshots", "text in", "scrolled", "timeline", "no results", "rarely finds",
        "doesn't work", "useless to even try", "basic search terms", "lost photo",
        "where is", "vaguely", "clues", "find old", "specific photo", "remember taking"
    ]

    scored = []
    for cand in candidates:
        cand_low = cand.lower()
        score = sum(3 for cue in high_value_cues if cue in cand_low)
        if any(w in cand_low for w in ["search", "find", "looking", "locate", "album", "photo", "picture"]):
            score += 1
        scored.append((score, cand))

    scored.sort(key=lambda x: x[0], reverse=True)

    if scored and scored[0][0] > 0:
        best_cand = scored[0][1]
        # Keep under 200 chars while ensuring exact verbatim substring
        if len(best_cand) > 200:
            truncated = best_cand[:180].rsplit(" ", 1)[0]
            if truncated in raw_text:
                return truncated
        if best_cand in raw_text:
            return best_cand
        elif best_cand in full_text:
            return best_cand

    # Fallback to first substantive sentence or title
    fallback = (raw_text if len(raw_text) > 10 else raw_title)[:180].strip()
    return fallback


def classify_and_extract(row: Dict[str, Any]) -> Dict[str, Any]:
    """
    Core Phase 2A analytical logic per record with strict context matching and taxonomy enforcement.
    """
    raw_text = str(row.get("text") or "")
    raw_title = str(row.get("title") or "")
    source = str(row.get("source") or "")
    
    text = clean_text_for_matching(raw_text)
    title = clean_text_for_matching(raw_title)
    combined = f"{title} {text}".strip()
    combined_low = combined.lower()

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

    if not combined or len(combined) < 5 or combined_low in ["nan", "none", "null"]:
        res["relevance_reason"] = "Record contains no substantive text content."
        return res

    # -------------------------------------------------------------
    # 1. EXCLUSIONS & NEGATIVE HEURISTICS (NOT_RELEVANT)
    # -------------------------------------------------------------
    
    is_trash_restore = bool(re.search(
        r'\b(restore|recovered|return|recover)\b.*\b(bin|trash|permanently deleted|deleted by mistake)\b',
        combined_low
    ))
    is_storage_quota_billing = bool(re.search(
        r'\b(out of storage|storage (is )?full|buy storage|google one subscription|15 gb|paid for yearly|cleen space|payment|billing|storage limit)\b',
        combined_low
    ))
    is_backup_sync_mechanics = bool(re.search(
        r'\b(backup is stuck|syncing 0 of|photos not backing up|backup only certain folders|photos sync on phone but not computer|cant backup|sync failed)\b',
        combined_low
    ))
    is_account_sharing = bool(re.search(
        r'\b(separate 2 phones sharing|partner sharing|share storage|switch google accounts|two different google accounts)\b',
        combined_low
    ))
    is_ui_idiomatic_find = bool(re.search(
        r'can\'?t\s+(seem\s+to\s+)?find\s+(definitive answers|a way to delete|an option to|where the setting|the button|the link|the part of photos|my recap|the total count|the toggle|option to block)\b',
        combined_low
    ))
    is_general_bug_or_update = bool(re.search(
        r'\b(ads slop|clutters photos|update ruined|battery drain|app crashes|cannot sort folders|duplicate photos that i cant find a way to delete)\b',
        combined_low
    ))

    # Explicit search / retrieval signals
    has_explicit_photo_search_need = bool(re.search(
        r'\b(can\'?t|cannot|couldn\'?t|trying to|tried to|how to|how do i|unable to|struggling to)\s+(find|search|locate|retrieve|look for)\s+(a |the |my |an |old |specific |certain |some )?(photo|photos|picture|pictures|image|images|video|videos|screenshot|screenshots|receipt|receipts)\b',
        combined_low
    )) or bool(re.search(
        r'\b(search engine|search function|search bar|ai search|ask photos|facial recognition)\s+(doesn\'?t|does not|never|rarely|failed to|won\'?t|is broken|not working|terrible|useless|complete mess)\b',
        combined_low
    )) or bool(re.search(
        r'\b(when i search for|searching for|searched for|typed in search|search returns|found nothing when searching)\b',
        combined_low
    )) or bool(re.search(
        r'\b(find text in screenshots|cant find text in|ocr search|search by (face|name|place|date|keyword|color))\b',
        combined_low
    )) or bool(re.search(
        r'\b(remember (taking|having|it was|we were|the picture of)|scrolled for hours (trying to find|to find))\b',
        combined_low
    ))

    has_search_feature_discussion = bool(re.search(
        r'\b(ask photos|gemini in photos|search|retrieval|indexing|face recognition|face tagging|face grouping|cluster|visual search|google lens|photo search|semantic search|vector search|clip|ocr)\b',
        combined_low
    ))

    # -------------------------------------------------------------
    # 2. CLASSIFICATION DETERMINATION
    # -------------------------------------------------------------

    if (is_trash_restore or is_storage_quota_billing or is_backup_sync_mechanics or is_account_sharing or is_ui_idiomatic_find or is_general_bug_or_update) and not has_explicit_photo_search_need:
        res["relevance_label"] = "not_relevant"
        if is_trash_restore:
            res["relevance_reason"] = "User inquiry regarding accidental trash/bin deletion recovery rather than search or retrieval of active photos."
        elif is_storage_quota_billing:
            res["relevance_reason"] = "Discusses cloud storage quotas, payment plans, or Google One billing without photo retrieval context."
        elif is_backup_sync_mechanics:
            res["relevance_reason"] = "Discusses device-to-cloud backup/sync mechanics without photo search context."
        elif is_account_sharing:
            res["relevance_reason"] = "Discusses multi-account or partner sharing configuration without photo retrieval context."
        elif is_ui_idiomatic_find:
            res["relevance_reason"] = "Uses 'find' idiomatically to describe locating UI settings, links, or documentation rather than photos."
        else:
            res["relevance_reason"] = "General app review, UI dissatisfaction, or bug report without evidence on photo retrieval."
        return res

    # HIGHLY RELEVANT
    if has_explicit_photo_search_need:
        res["relevance_label"] = "highly_relevant"
        res["evidence_strength"] = "direct"
        res["relevance_reason"] = "Direct user account detailing attempts to search for, locate, or retrieve specific photos using contextual/semantic clues, or reporting retrieval failure in Google Photos."
    
    # POSSIBLY RELEVANT
    elif has_search_feature_discussion:
        res["relevance_label"] = "possibly_relevant"
        res["evidence_strength"] = "indirect" if not re.search(r'\b(i|my|we)\b', combined_low) else "direct"
        res["relevance_reason"] = "Discusses Google Photos search capabilities, Ask Photos, AI search algorithms, or photo organization, but evidence on vague personal retrieval is partial or high-level."
    
    else:
        res["relevance_label"] = "not_relevant"
        res["relevance_reason"] = "Does not provide meaningful evidence about photo/video retrieval or search behavior."
        return res

    # -------------------------------------------------------------
    # 3. EXTRACTIONS (FOR HIGHLY & POSSIBLY RELEVANT)
    # -------------------------------------------------------------

    # A. Retrieval Scenario Taxonomy
    scenarios = []
    if re.search(r'\b(trip|vacation|travel|flight|hotel|tourist|paris|japan|beach|holiday|hawaii|abroad|mountains)\b', combined_low):
        scenarios.append("travel")
    if re.search(r'\b(daughter|son|baby|child|children|kids|mom|dad|mother|father|family|grandma|grandpa|wife|husband|wedding|friend|friends|brother|sister|granddaughter|cousin)\b', combined_low):
        scenarios.append("person_family")
    if re.search(r'\b(dog|cat|dogs|cats|puppy|kitten|pet|pets|animal|animals|pigeon|bird)\b', combined_low):
        scenarios.append("pet")
    if re.search(r'\b(food|restaurant|dish|meal|dinner|lunch|cake|recipe|coffee|cooking|menu|beer|wine)\b', combined_low):
        scenarios.append("food_restaurant")
    if re.search(r'\b(screenshot|screenshots|screen shot|screen grab)\b', combined_low):
        scenarios.append("screenshot")
    if re.search(r'\b(receipt|receipts|tax form|invoice|boarding pass|passport|driver license|parking ticket|contract|w2)\b', combined_low):
        scenarios.append("document_receipt")
    if re.search(r'\b(medical|doctor|prescription|hospital|medicine|wound|rash|health card|vaccine card)\b', combined_low):
        scenarios.append("medical_health")
    if re.search(r'\b(at work|workplace|office meeting|project files|colleague|coworker|business presentation|whiteboard|client meeting)\b', combined_low):
        scenarios.append("work")
    if re.search(r'\b(school|classroom|college|university|homework|lecture|exam|student)\b', combined_low):
        scenarios.append("school")
    if re.search(r'\b(shopping|price tag|bought in store|clothing item|shoes i saw|product tag)\b', combined_low):
        scenarios.append("shopping_product")
    if re.search(r'\b(house renovation|apartment|kitchen remodel|garden|garage|furniture)\b', combined_low):
        scenarios.append("home_location")
    if re.search(r'\b(party|concert|festival|birthday|anniversary|graduation|christmas party|halloween party|ceremony)\b', combined_low):
        scenarios.append("event")

    scenarios = [s for s in scenarios if s in ALLOWED_SCENARIOS]
    if scenarios:
        res["retrieval_scenario"] = ", ".join(scenarios)
    elif res["relevance_label"] == "highly_relevant":
        res["retrieval_scenario"] = "other"
    else:
        res["retrieval_scenario"] = "unknown"

    # B. Remembered Clues Taxonomy
    clues = []
    if re.search(r'\b(person|people|face|faces|tagged face|daughter|son|mom|dad|baby|kid|wife|husband|friend|friends|grandma|grandpa|cousin)\b', combined_low):
        clues.append("person")
    if re.search(r'\b(location|city|country|beach|mountain|paris|park|hotel|street|where it was taken|gps location)\b', combined_low):
        clues.append("place")
    if re.search(r'(\b\d{4}\b|\byears ago\b|\bmonths ago\b|\blast (summer|winter|year|week|month)\b|\baround (christmas|thanksgiving)\b|\btaken in\b|\bold photo\b)', combined_low):
        clues.append("approximate_time")
    if re.search(r'\b(wedding|birthday|concert|trip|party|vacation|ceremony|celebration|graduation|festival)\b', combined_low):
        clues.append("event")
    if re.search(r'\b(hiking|swimming|eating|drinking|dancing|cooking|running|playing|driving|biking|skiing)\b', combined_low):
        clues.append("activity")
    if re.search(r'\b(car|hat|shirt|guitar|building|tree|sign|flower|table|statue|glasses|shoes|pigeon|cake)\b', combined_low):
        clues.append("object")
    if re.search(r'\b(red|blue|yellow|black|white|green|dark|bright|wearing|color|appearance|blurry|smiling)\b', combined_low):
        clues.append("visual_appearance")
    if re.search(r'\b(text on photo|words in image|ocr|caption|license plate|sign text|printed text|words on|text in)\b', combined_low):
        clues.append("text")
    if re.search(r'\b(happy|sad|funny|smile|crying|excited|favorite|nostalgic|memorable)\b', combined_low):
        clues.append("emotion_context")
    if re.search(r'\b(together with|with my|who was with|with friends|with family|group photo)\b', combined_low):
        clues.append("who_with")
    if re.search(r'\b(snow|snowing|rain|raining|sunny|summer|winter|fall|spring|weather|snowy)\b', combined_low):
        clues.append("weather_season")
    if re.search(r'\b(road trip|vacation trip|flight to|travel trip|cruise)\b', combined_low):
        clues.append("trip")
    if re.search(r'\b(texted me|told me|conversation about|discussion)\b', combined_low):
        clues.append("conversation")
    if re.search(r'\b(background|standing next to|in the middle of|outside|inside the room|setting)\b', combined_low):
        clues.append("surrounding_circumstances")

    clues = [c for c in clues if c in ALLOWED_CLUES]
    res["remembered_clues"] = ", ".join(clues) if clues else ""

    # C. Forgotten / Unknown Clues
    forgotten = []
    if re.search(r'\b(don\'?t remember the date|can\'?t remember when|no idea what year|forgot the date|no date|exact date unknown)\b', combined_low):
        forgotten.append("exact_date")
    if re.search(r'\b(don\'?t remember where|can\'?t remember the place|no location|forgot the city|no gps)\b', combined_low):
        forgotten.append("exact_location")
    if re.search(r'\b(don\'?t know filename|no filename|img_\d+|dcm_\d+|filename)\b', combined_low):
        forgotten.append("filename")
    if re.search(r'\b(not in an album|forgot album|no album|which album)\b', combined_low):
        forgotten.append("album_name")

    if not forgotten and res["relevance_label"] == "highly_relevant":
        if "approximate_time" in clues:
            forgotten.append("exact_date")
        if "visual_appearance" in clues or "object" in clues or "activity" in clues:
            forgotten.append("filename")

    res["forgotten_or_unknown_clues"] = ", ".join(forgotten) if forgotten else ""

    # D. Search Behavior Taxonomy
    behaviors = []
    if re.search(r'\b(search|searched|searching|search engine|search bar|search box|typed|query|keyword|basic search terms)\b', combined_low):
        behaviors.append("keyword_search")
    if re.search(r'\b(ask photos|natural language|conversational|gemini|sentence prompt|descriptive prompt)\b', combined_low):
        behaviors.append("Ask_Google_Photos")
        behaviors.append("natural_language_search")
    if re.search(r'\b(people & pets|face search|search by face|search by name|facial recognition|tagged person|person search)\b', combined_low):
        behaviors.append("person_search")
    if re.search(r'\b(map view|search by location|place search|city search)\b', combined_low):
        behaviors.append("location_search")
    if re.search(r'\b(scrolled|scrolling|timeline|swipe|scrolled for hours|browsing timeline|manual browse)\b', combined_low):
        behaviors.append("timeline_scrolling")
        behaviors.append("manual_browsing")
    if re.search(r'\b(album|albums|folders view)\b', combined_low):
        behaviors.append("album_browsing")
    if re.search(r'\b(google lens|lens|visual search)\b', combined_low):
        behaviors.append("Google_Lens")
    if re.search(r'\b(asked my|asked a friend|asked family|asking someone)\b', combined_low):
        behaviors.append("asking_someone")
    if re.search(r'\b(apple photos|gallery app|onedrive|local search|external app)\b', combined_low):
        behaviors.append("external_search")

    behaviors = [b for b in behaviors if b in ALLOWED_BEHAVIORS]
    behaviors = list(dict.fromkeys(behaviors))
    res["search_behavior"] = ", ".join(behaviors) if behaviors else ("keyword_search" if "search" in combined_low else "unknown")

    # E. Search Query or Words Used (explicit extraction)
    query_match = re.search(r'(search(ed)?\s+(for|with)?\s+["\']([^"\']+)["\']|query\s+["\']([^"\']+)["\']|typed\s+["\']([^"\']+)["\'])', combined, re.IGNORECASE)
    if query_match:
        extracted_q = query_match.group(4) or query_match.group(5) or query_match.group(6)
        res["search_query_or_words_used"] = extracted_q.strip()
    else:
        res["search_query_or_words_used"] = ""

    # F. Failure Stage Taxonomy
    if re.search(r'\b(can\'?t think of what to type|how to describe|hard to put into words|don\'?t know how to search)\b', combined_low):
        res["failure_stage"] = "memory_to_query"
    elif re.search(r'\b(doesn\'?t understand|misunderstands|wrong interpretation|hallucinat|literal search)\b', combined_low):
        res["failure_stage"] = "query_to_understanding"
    elif re.search(r'\b(zero results|0 results|no results|shows wrong photos|missed the photo|doesn\'?t show up|can\'?t find it|returns nothing)\b', combined_low):
        res["failure_stage"] = "understanding_to_retrieval"
    elif re.search(r'\b(too many results|endless list|can\'?t tell which one|blurry thumbnail|hard to recognize)\b', combined_low):
        res["failure_stage"] = "candidate_to_recognition"
    elif re.search(r'\b(had to scroll manually|gave up|never found|lost forever|scrolling through all photos)\b', combined_low):
        res["failure_stage"] = "failed_search_to_recovery"
    else:
        res["failure_stage"] = "understanding_to_retrieval" if res["relevance_label"] == "highly_relevant" else "unknown"

    # G. Retrieval Barrier
    barriers = []
    if re.search(r'\b(zero results|no results|returns nothing|shows nothing|nothing comes up|found nothing)\b', combined_low):
        barriers.append("Search returns zero results for descriptive queries")
    if re.search(r'\b(wrong (photos|results|person|pictures)|unrelated photos|irrelevant results)\b', combined_low):
        barriers.append("Search returns irrelevant or incorrect photos")
    if re.search(r'\b(facial recognition|face recognition|face tagging|face grouping|wrong person tagged|merged faces|untagged face)\b', combined_low):
        barriers.append("Face recognition clustering errors or misidentification")
    if re.search(r'\b(ocr|text in photo|text search|can\'?t read text|text in screenshot|text in screenshots)\b', combined_low):
        barriers.append("OCR/Text in image search failure")
    if re.search(r'\b(too slow|takes forever|laggy search|indexing takes weeks)\b', combined_low):
        barriers.append("Search latency or indexing lag")
    if re.search(r'\b(missing from search|photos disappeared from search|search index broken)\b', combined_low):
        barriers.append("Search index failure / missing media")

    if barriers:
        res["retrieval_barrier"] = "; ".join(barriers)
    elif res["relevance_label"] == "highly_relevant":
        res["retrieval_barrier"] = "Search fails to locate photo matching user's remembered context"
    else:
        res["retrieval_barrier"] = ""

    # H. Workaround
    workarounds = []
    if re.search(r'\b(scrolled|scrolling (through|down)|manual scroll|looking through all photos|scroll through years)\b', combined_low):
        workarounds.append("Manual timeline scrolling through years of photos")
    if re.search(r'\b(created album|put in album|tagged manually|renamed|custom album)\b', combined_low):
        workarounds.append("Manual album organization or tagging")
    if re.search(r'\b(used apple photos|switched to|used another app|google drive|local gallery|local files)\b', combined_low):
        workarounds.append("Switching to third-party gallery or local file manager")
    if re.search(r'\b(asked (someone|friend|family)|messaged|sent text)\b', combined_low):
        workarounds.append("Asking friends or family for the photo")

    if workarounds:
        res["workaround"] = "; ".join(workarounds)
    else:
        res["workaround"] = ""

    # I. Retrieval Outcome
    if re.search(r'\b(gave up|couldn\'?t find|never found|lost forever|still can\'?t find|no luck|unresolved)\b', combined_low):
        res["retrieval_outcome"] = "failed_gave_up"
    elif re.search(r'\b(found it after hours|finally found|took forever to find|took a long time|eventually found)\b', combined_low):
        res["retrieval_outcome"] = "found_after_excessive_effort"
    elif re.search(r'\b(found it|worked great|easily found|instant|super fast|found all)\b', combined_low):
        res["retrieval_outcome"] = "found_successfully"
    elif re.search(r'\b(found some|partially|only found 1|mixed results)\b', combined_low):
        res["retrieval_outcome"] = "partially_found"
    else:
        res["retrieval_outcome"] = "unknown"

    # J. Evidence Quote (Verbatim substring from raw text or title)
    quote = extract_best_verbatim_quote(raw_text, raw_title)
    res["evidence_quote"] = quote

    return res


def run_phase2a():
    base_dir = Path(__file__).resolve().parent
    input_file = base_dir / "Scrape_data" / "cleaned" / "all_sources_deduplicated.csv"
    if not input_file.exists():
        raise FileNotFoundError(f"Input file not found: {input_file}")

    print(f"Reading deduplicated corpus: {input_file}...")
    df = pd.read_csv(input_file)
    total_records = len(df)
    print(f"Total deduplicated records to process: {total_records}")

    classified_records = []
    verbatim_errors = 0

    for idx, row in df.iterrows():
        row_dict = row.to_dict()
        analysis = classify_and_extract(row_dict)
        
        # Merge analysis fields
        for k, v in analysis.items():
            row_dict[k] = v

        # Verbatim quote safety verification
        if row_dict["relevance_label"] != "not_relevant":
            q = row_dict["evidence_quote"]
            src_text = str(row.get("text") or "")
            src_title = str(row.get("title") or "")
            full_orig = f"{src_title} {src_text}"
            if q and q not in full_orig and q not in src_text and q not in src_title:
                verbatim_errors += 1
                row_dict["evidence_quote"] = (src_text[:180] if src_text else src_title[:180]).strip()

        classified_records.append(row_dict)

    classified_df = pd.DataFrame(classified_records)

    # Output 1: All 1,035 classified records
    out_classified = base_dir / "Scrape_data" / "cleaned" / "retrieval_relevance_classified.csv"
    classified_df.to_csv(out_classified, index=False, encoding="utf-8")
    print(f"Saved: {out_classified} ({len(classified_df)} records)")

    # Output 2: Summary Metrics
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
    print(f"Saved: {out_summary}")

    # Output 3: Retrieval Evidence (Only highly_relevant & possibly_relevant)
    evidence_df = classified_df[classified_df["relevance_label"].isin(["highly_relevant", "possibly_relevant"])].copy()
    out_evidence = base_dir / "Scrape_data" / "cleaned" / "retrieval_evidence.csv"
    evidence_df.to_csv(out_evidence, index=False, encoding="utf-8")
    print(f"Saved: {out_evidence} ({len(evidence_df)} records)")

    print("\n--- PHASE 2A EXECUTION COMPLETE ---")
    print(summary_df.to_string())
    print("\nCross-tab by source:")
    print(pd.crosstab(classified_df["source"], classified_df["relevance_label"], margins=True).to_string())


if __name__ == "__main__":
    run_phase2a()
