"""
Apple App Store Collector for Google Photos.
Target App ID: 962194608 (Google Photos for iOS)
Collects public user reviews via Apple iTunes Customer Reviews public feed.
"""

import logging
import time
from typing import Any, Dict, List, Optional
import requests
from utils.normalization import normalize_record

logger = logging.getLogger(__name__)

APP_ID = "962194608"


def fetch_itunes_rss_reviews(limit: int = 50, country: str = "us") -> List[Dict[str, Any]]:
    """
    Fetches customer reviews from the public Apple iTunes RSS JSON feed.
    This is an open, public Apple endpoint that requires no credentials.
    """
    raw_reviews = []
    page = 1
    max_pages = max(1, limit // 10 + 2)

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
    }

    while len(raw_reviews) < limit and page <= max_pages:
        url = f"https://itunes.apple.com/{country}/rss/customerreviews/page={page}/id={APP_ID}/sortBy=mostRecent/json"
        try:
            resp = requests.get(url, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                feed = data.get("feed", {})
                entries = feed.get("entry", [])
                if not entries:
                    break

                for entry in entries:
                    if "im:rating" in entry:
                        raw_reviews.append(entry)
                        if len(raw_reviews) >= limit * 2:
                            break
            else:
                logger.warning(f"iTunes RSS returned status code {resp.status_code} for page {page}")
                break
        except Exception as e:
            logger.warning(f"Failed to fetch iTunes RSS page {page}: {e}")
            break

        page += 1
        time.sleep(0.5)

    return raw_reviews


def collect_app_store_reviews(
    queries: Optional[List[str]] = None,
    limit: int = 50,
    country: str = "us",
) -> List[Dict[str, Any]]:
    """
    Collects Apple App Store reviews for Google Photos, normalizing schema and prioritizing retrieval topics.
    """
    logger.info(f"Starting Apple App Store collection for ID {APP_ID} (limit={limit})...")
    normalized_records: List[Dict[str, Any]] = []

    try:
        raw_entries = fetch_itunes_rss_reviews(limit=max(limit * 2, 60), country=country)
        search_keywords = [q.lower() for q in (queries or ["search", "find", "photo", "album", "timeline"])]

        prioritized = []
        others = []

        for entry in raw_entries:
            title = entry.get("title", {}).get("label", "")
            content = entry.get("content", {}).get("label", "")
            full_text = f"{title}\n{content}".strip()
            
            matched_query = ""
            for kw in search_keywords:
                if kw in full_text.lower():
                    matched_query = kw
                    break

            if matched_query:
                prioritized.append((entry, matched_query))
            else:
                others.append((entry, ""))

        selected = prioritized[:limit]
        if len(selected) < limit:
            selected.extend(others[: limit - len(selected)])

        for entry, query_tag in selected:
            review_id = str(entry.get("id", {}).get("label", "")).strip()
            author = entry.get("author", {}).get("name", {}).get("label", "App Store User")
            rating = entry.get("im:rating", {}).get("label", "")
            title = entry.get("title", {}).get("label", "")
            content = entry.get("content", {}).get("label", "")
            published_at = entry.get("updated", {}).get("label", "")

            norm = normalize_record(
                raw={
                    "source": "app_store",
                    "platform": "ios",
                    "source_id": review_id,
                    "url": f"https://apps.apple.com/us/app/google-photos/id{APP_ID}?reviewId={review_id}",
                    "title": title,
                    "author": author,
                    "text": content or title,
                    "published_at": published_at,
                    "rating": rating,
                    "language": "en",
                    "search_query": query_tag or "general_reviews",
                },
                default_source="app_store",
                default_platform="ios",
            )
            normalized_records.append(norm)

        logger.info(f"App Store collection completed. Collected {len(normalized_records)} records.")
    except Exception as e:
        logger.error(f"Error during App Store collection: {e}", exc_info=True)

    return normalized_records
