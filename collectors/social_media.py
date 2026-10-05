"""
Public Social Media Collector for Google Photos.
Collects public posts from open, accessible social platforms (e.g., Lemmy Fediverse Public API, Bluesky, Mastodon)
concerning Google Photos search failures, Ask Photos experiences, and photo retrieval frustrations.
"""

import logging
import time
from typing import Any, Dict, List, Optional
import requests
from utils.normalization import normalize_record

logger = logging.getLogger(__name__)


def fetch_lemmy_posts(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """
    Fetches real public user posts from Lemmy (open fediverse platform) using its public search API.
    """
    results = []
    url = "https://lemmy.world/api/v3/search"
    headers = {"User-Agent": "GooglePhotosDiscoveryEngineResearch/1.0 (academic PM research)"}
    params = {
        "q": f"Google Photos {query}",
        "type_": "Posts",
        "sort": "TopAll",
        "limit": min(50, max(5, limit)),
    }

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=12)
        if resp.status_code == 200:
            data = resp.json()
            posts = data.get("posts", [])
            for item in posts:
                post_info = item.get("post", {})
                creator = item.get("creator", {})
                counts = item.get("counts", {})

                post_id = post_info.get("id")
                title = post_info.get("name", "")
                body = post_info.get("body", "")
                published_at = post_info.get("published", "")
                url_link = post_info.get("ap_id", "")
                author = creator.get("name", "Lemmy User")
                score = counts.get("score", 0)

                full_text = f"{title}\n{body}".strip() if body else title
                if not full_text:
                    continue

                results.append({
                    "id": str(post_id),
                    "url": url_link,
                    "title": title,
                    "author": author,
                    "text": full_text,
                    "published_at": published_at,
                    "rating": score,
                    "platform": "lemmy_social",
                })
                if len(results) >= limit:
                    break
        else:
            logger.warning(f"Lemmy search returned status {resp.status_code} for query '{query}'")

    except Exception as e:
        logger.warning(f"Error querying Lemmy API for '{query}': {e}")

    return results


def fetch_bluesky_posts(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Fetches public user posts from Bluesky AT Protocol search API."""
    results = []
    url = "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts"
    headers = {"User-Agent": "GooglePhotosDiscoveryEngineResearch/1.0"}
    params = {"q": f"Google Photos {query}", "limit": min(50, max(5, limit))}

    try:
        resp = requests.get(url, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            posts = data.get("posts", [])
            for p in posts:
                uri = p.get("uri", "")
                cid = p.get("cid", "")
                author_handle = p.get("author", {}).get("handle", "bsky_user")
                record_data = p.get("record", {})
                text = record_data.get("text", "")
                created_at = record_data.get("createdAt", "")
                like_count = p.get("likeCount", 0)

                rkey = uri.split("/")[-1] if uri else ""
                web_url = f"https://bsky.app/profile/{author_handle}/post/{rkey}" if rkey else ""

                if not text:
                    continue

                results.append({
                    "id": cid or rkey or uri,
                    "url": web_url,
                    "title": "",
                    "author": f"@{author_handle}",
                    "text": text,
                    "published_at": created_at,
                    "rating": like_count,
                    "platform": "bluesky",
                })
                if len(results) >= limit:
                    break
    except Exception as e:
        logger.debug(f"Bluesky public search error: {e}")

    return results


def collect_social_media_posts(
    queries: Optional[List[str]] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Collects real discussions from publicly accessible social media APIs.
    """
    logger.info(f"Starting Public Social Media collection (limit={limit})...")
    normalized_records: List[Dict[str, Any]] = []

    query_list = queries or [
        "search",
        "can't find",
        "Ask Photos",
        "find photo",
        "search broken",
    ]

    seen_ids = set()
    per_query_limit = max(5, limit // len(query_list) + 2)

    for query in query_list:
        if len(normalized_records) >= limit:
            break

        # 1. Lemmy Fediverse Open Public API
        lemmy_items = fetch_lemmy_posts(query, limit=per_query_limit)
        for item in lemmy_items:
            i_id = item.get("id")
            if not i_id or i_id in seen_ids:
                continue
            seen_ids.add(i_id)

            norm = normalize_record(
                raw={
                    "source": "social_media",
                    "platform": item.get("platform", "lemmy_social"),
                    "source_id": str(i_id),
                    "url": item.get("url"),
                    "title": item.get("title"),
                    "author": item.get("author"),
                    "text": item.get("text"),
                    "published_at": item.get("published_at"),
                    "rating": item.get("rating"),
                    "language": "en",
                    "search_query": query,
                },
                default_source="social_media",
                default_platform="lemmy_social",
            )
            normalized_records.append(norm)
            if len(normalized_records) >= limit:
                break

        time.sleep(0.5)

        # 2. Bluesky fallback
        if len(normalized_records) < limit:
            bsky_items = fetch_bluesky_posts(query, limit=per_query_limit)
            for item in bsky_items:
                i_id = item.get("id")
                if not i_id or i_id in seen_ids:
                    continue
                seen_ids.add(i_id)

                norm = normalize_record(
                    raw={
                        "source": "social_media",
                        "platform": "bluesky",
                        "source_id": str(i_id),
                        "url": item.get("url"),
                        "title": item.get("title"),
                        "author": item.get("author"),
                        "text": item.get("text"),
                        "published_at": item.get("published_at"),
                        "rating": item.get("rating"),
                        "language": "en",
                        "search_query": query,
                    },
                    default_source="social_media",
                    default_platform="bluesky",
                )
                normalized_records.append(norm)
                if len(normalized_records) >= limit:
                    break

        time.sleep(0.5)

    logger.info(f"Public Social Media collection completed. Collected {len(normalized_records)} records.")
    return normalized_records
