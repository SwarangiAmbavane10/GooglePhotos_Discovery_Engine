"""
Google Photos Help Community Collector.
Source: support.google.com/photos/threads
Collects public user help requests, problem reports, and search failure discussions.
"""

import logging
import re
import time
from typing import Any, Dict, List, Optional
import requests
from bs4 import BeautifulSoup
from utils.normalization import normalize_record

logger = logging.getLogger(__name__)


def fetch_community_threads(query: Optional[str] = None, limit: int = 30) -> List[Dict[str, Any]]:
    """
    Fetches public forum threads from the Google Photos Help Community.
    """
    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
    }

    url = "https://support.google.com/photos/threads"
    params = {
        "hl": "en",
        "max_results": str(max(limit * 2, 60)),
    }
    if query:
        params["query"] = query

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Find all thread anchors
            thread_links = soup.find_all("a", href=re.compile(r"/photos/thread/\d+"))
            
            seen_thread_ids = set()
            for link in thread_links:
                href = link.get("href", "")
                thread_id_match = re.search(r"/photos/thread/(\d+)", href)
                if not thread_id_match:
                    continue
                thread_id = thread_id_match.group(1)
                if thread_id in seen_thread_ids:
                    continue
                seen_thread_ids.add(thread_id)

                title = link.get_text(" ", strip=True)
                full_url = f"https://support.google.com/photos/thread/{thread_id}"
                
                # Extract parent text or snippet
                parent = link.find_parent("div")
                snippet = parent.get_text(" ", strip=True) if parent else title

                if not title and not snippet:
                    continue

                results.append({
                    "thread_id": thread_id,
                    "url": full_url,
                    "title": title,
                    "text": snippet if len(snippet) > len(title) else title,
                })
                
                if len(results) >= limit:
                    break

        else:
            logger.warning(f"Google Support Community returned status {resp.status_code} for query '{query}'")

    except Exception as e:
        logger.warning(f"Error fetching Google Support Community for query '{query}': {e}")

    return results


def collect_google_photos_community(
    queries: Optional[List[str]] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Collects real user questions and reports from the official Google Photos Help Community.
    """
    logger.info(f"Starting Google Photos Help Community collection (limit={limit})...")
    normalized_records: List[Dict[str, Any]] = []

    query_list = queries or [
        "can't find photo",
        "search not working",
        "find old photos",
        "search missing photos",
        "Ask Photos",
        "find screenshot",
    ]

    seen_ids = set()
    
    # 1. Search specific retrieval queries
    for query in query_list:
        if len(normalized_records) >= limit:
            break
        
        threads = fetch_community_threads(query=query, limit=10)
        for t in threads:
            t_id = t.get("thread_id")
            if not t_id or t_id in seen_ids:
                continue
            seen_ids.add(t_id)

            norm = normalize_record(
                raw={
                    "source": "google_photos_community",
                    "platform": "google_help",
                    "source_id": t_id,
                    "url": t.get("url"),
                    "title": t.get("title"),
                    "author": "Help Community User",
                    "text": t.get("text") or t.get("title"),
                    "published_at": "",
                    "rating": "",
                    "language": "en",
                    "search_query": query,
                },
                default_source="google_photos_community",
                default_platform="google_help",
            )
            normalized_records.append(norm)

            if len(normalized_records) >= limit:
                break

        time.sleep(0.5)

    # 2. General threads if still under limit
    if len(normalized_records) < limit:
        general_threads = fetch_community_threads(query=None, limit=limit - len(normalized_records) + 5)
        for t in general_threads:
            t_id = t.get("thread_id")
            if not t_id or t_id in seen_ids:
                continue
            seen_ids.add(t_id)

            norm = normalize_record(
                raw={
                    "source": "google_photos_community",
                    "platform": "google_help",
                    "source_id": t_id,
                    "url": t.get("url"),
                    "title": t.get("title"),
                    "author": "Help Community User",
                    "text": t.get("text") or t.get("title"),
                    "published_at": "",
                    "rating": "",
                    "language": "en",
                    "search_query": "community_threads",
                },
                default_source="google_photos_community",
                default_platform="google_help",
            )
            normalized_records.append(norm)

            if len(normalized_records) >= limit:
                break

    logger.info(f"Google Photos Help Community collection completed. Collected {len(normalized_records)} records.")
    return normalized_records
