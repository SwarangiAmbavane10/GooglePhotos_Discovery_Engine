"""
Google Play Store Collector for Google Photos.
Target App: com.google.android.apps.photos
Collects public user reviews with a focus on photo/video retrieval and search topics.
"""

import logging
import time
from typing import Any, Dict, List, Optional
from google_play_scraper import reviews, Sort
from utils.normalization import normalize_record

logger = logging.getLogger(__name__)

PACKAGE_NAME = "com.google.android.apps.photos"


def collect_google_play_reviews(
    queries: Optional[List[str]] = None,
    limit: int = 50,
    lang: str = "en",
    country: str = "us",
) -> List[Dict[str, Any]]:
    """
    Collects reviews from the Google Play Store for Google Photos.
    Matches queries/keywords against reviews to prioritize retrieval topics.
    """
    logger.info(f"Starting Google Play collection for {PACKAGE_NAME} (limit={limit})...")
    normalized_records: List[Dict[str, Any]] = []
    
    # We fetch a larger batch of reviews to find relevant retrieval/search ones
    fetch_count = max(limit * 4, 150)
    
    try:
        # Fetch newest and most relevant reviews
        all_raw_reviews = []
        for sort_type in [Sort.NEWEST, Sort.MOST_RELEVANT]:
            try:
                res, _ = reviews(
                    PACKAGE_NAME,
                    lang=lang,
                    country=country,
                    sort=sort_type,
                    count=fetch_count // 2,
                    filter_score_with=None,
                )
                all_raw_reviews.extend(res)
                time.sleep(0.5)
            except Exception as e:
                logger.warning(f"Google Play fetch with sort {sort_type} failed: {e}")

        # Remove duplicates from raw batch
        seen_ids = set()
        unique_reviews = []
        for r in all_raw_reviews:
            r_id = r.get("reviewId")
            if r_id and r_id not in seen_ids:
                seen_ids.add(r_id)
                unique_reviews.append(r)

        search_keywords = [q.lower() for q in (queries or ["search", "find", "photo", "album", "timeline"])]

        # Score and prioritize retrieval-related reviews
        prioritized = []
        others = []

        for r in unique_reviews:
            content = (r.get("content") or "").lower()
            matched_query = ""
            for kw in search_keywords:
                if kw in content:
                    matched_query = kw
                    break
            
            if matched_query:
                prioritized.append((r, matched_query))
            else:
                others.append((r, ""))

        # Combine: take prioritized first, then others up to limit
        selected = prioritized[:limit]
        if len(selected) < limit:
            selected.extend(others[: limit - len(selected)])

        for r, query_tag in selected:
            norm = normalize_record(
                raw={
                    "source": "google_play",
                    "platform": "android",
                    "source_id": r.get("reviewId"),
                    "url": f"https://play.google.com/store/apps/details?id={PACKAGE_NAME}&reviewId={r.get('reviewId')}",
                    "title": "",
                    "author": r.get("userName") or "Google Play User",
                    "text": r.get("content") or "",
                    "published_at": r.get("at"),
                    "rating": r.get("score"),
                    "language": lang,
                    "search_query": query_tag or "general_reviews",
                },
                default_source="google_play",
                default_platform="android",
            )
            normalized_records.append(norm)

        logger.info(f"Google Play collection completed. Collected {len(normalized_records)} records.")
    except Exception as e:
        logger.error(f"Error during Google Play collection: {e}", exc_info=True)

    return normalized_records
