"""
Public Forums Collector for Google Photos.
Collects public discussions from developer and tech forums (e.g., Hacker News Algolia API, tech discussion boards)
focused on Google Photos search architecture, search regressions, Ask Photos, and photo retrieval problems.
"""

import logging
import time
from typing import Any, Dict, List, Optional
import requests
from utils.normalization import normalize_record

logger = logging.getLogger(__name__)


def fetch_hn_forum_discussions(query: str, limit: int = 25) -> List[Dict[str, Any]]:
    """
    Fetches genuine public forum comments and stories from Hacker News via its open Algolia Search API.
    """
    results = []
    url = "https://hn.algolia.com/api/v1/search"
    headers = {"User-Agent": "GooglePhotosDiscoveryEngineResearch/1.0"}

    # Search for comments mentioning the query
    params = {
        "query": f"Google Photos {query}",
        "tags": "(story,comment)",
        "hitsPerPage": min(50, limit * 2),
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            hits = data.get("hits", [])
            for hit in hits:
                hit_id = hit.get("objectID")
                comment_text = hit.get("comment_text") or hit.get("story_text") or ""
                title = hit.get("title") or hit.get("story_title") or ""
                author = hit.get("author") or "HN User"
                created_at = hit.get("created_at")
                points = hit.get("points") or 0
                story_id = hit.get("story_id") or hit_id
                item_url = f"https://news.ycombinator.com/item?id={hit_id}"

                # Only include substantive text
                full_text = comment_text if comment_text else title
                if not full_text:
                    continue

                results.append({
                    "id": hit_id,
                    "url": item_url,
                    "title": title,
                    "author": author,
                    "text": full_text,
                    "published_at": created_at,
                    "rating": points,
                })
                if len(results) >= limit:
                    break
        else:
            logger.warning(f"HN Algolia search returned status {resp.status_code} for '{query}'")

    except Exception as e:
        logger.warning(f"Error querying HN Algolia API for '{query}': {e}")

    return results


def collect_forum_discussions(
    queries: Optional[List[str]] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Collects real discussions from public technology and developer forums.
    """
    logger.info(f"Starting Public Forums collection (limit={limit})...")
    normalized_records: List[Dict[str, Any]] = []

    query_list = queries or [
        "search",
        "can't find photo",
        "Ask Photos",
        "AI search",
        "search regression",
        "find screenshot",
    ]

    seen_ids = set()
    per_query_limit = max(5, limit // len(query_list) + 2)

    for query in query_list:
        if len(normalized_records) >= limit:
            break

        discussions = fetch_hn_forum_discussions(query, limit=per_query_limit)
        for d in discussions:
            d_id = d.get("id")
            if not d_id or d_id in seen_ids:
                continue
            seen_ids.add(d_id)

            norm = normalize_record(
                raw={
                    "source": "forums",
                    "platform": "hacker_news",
                    "source_id": str(d_id),
                    "url": d.get("url"),
                    "title": d.get("title"),
                    "author": d.get("author"),
                    "text": d.get("text"),
                    "published_at": d.get("published_at"),
                    "rating": d.get("rating"),
                    "language": "en",
                    "search_query": query,
                },
                default_source="forums",
                default_platform="hacker_news",
            )
            normalized_records.append(norm)

            if len(normalized_records) >= limit:
                break

        time.sleep(0.5)

    logger.info(f"Public Forums collection completed. Collected {len(normalized_records)} records.")
    return normalized_records
