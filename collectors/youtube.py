"""
YouTube Comments and Video Discussions Collector.
Collects public user discussions and comments on Google Photos search demonstrations,
Ask Photos announcements, and retrieval tutorial videos.
Uses YouTube Data API v3 when YOUTUBE_API_KEY is available.
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional
import requests
from utils.normalization import normalize_record

from dotenv import load_dotenv

logger = logging.getLogger(__name__)


def collect_via_youtube_api(
    api_key: str,
    queries: List[str],
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Collects YouTube comments and video discussions using the official YouTube Data API v3."""
    from googleapiclient.discovery import build

    normalized_records: List[Dict[str, Any]] = []
    try:
        youtube = build("youtube", "v3", developerKey=api_key)
        per_query_limit = max(3, limit // max(1, len(queries)))

        for query in queries:
            if len(normalized_records) >= limit:
                break

            # 1. Search for relevant videos
            try:
                search_response = (
                    youtube.search()
                    .list(
                        q=query,
                        part="id,snippet",
                        maxResults=per_query_limit,
                        type="video",
                        relevanceLanguage="en",
                    )
                    .execute()
                )
            except Exception as q_err:
                logger.warning(f"Search query '{query}' failed: {q_err}")
                continue

            video_items = search_response.get("items", [])
            for v_item in video_items:
                if len(normalized_records) >= limit:
                    break

                video_id = v_item.get("id", {}).get("videoId")
                v_title = v_item.get("snippet", {}).get("title", "")
                if not video_id:
                    continue

                # 2. Fetch top comments for each video
                try:
                    comments_resp = (
                        youtube.commentThreads()
                        .list(
                            part="id,snippet",
                            videoId=video_id,
                            maxResults=10,
                            textFormat="plainText",
                            order="relevance",
                        )
                        .execute()
                    )

                    for c_item in comments_resp.get("items", []):
                        top_comment = c_item.get("snippet", {}).get("topLevelComment", {}).get("snippet", {})
                        comment_id = c_item.get("id")
                        author = top_comment.get("authorDisplayName", "YouTube User")
                        text_display = top_comment.get("textDisplay", "")
                        published_at = top_comment.get("publishedAt", "")
                        like_count = top_comment.get("likeCount", 0)

                        norm = normalize_record(
                            raw={
                                "source": "youtube",
                                "platform": "youtube",
                                "source_id": comment_id,
                                "url": f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}",
                                "title": f"Comment on: {v_title}",
                                "author": author,
                                "text": text_display,
                                "published_at": published_at,
                                "rating": like_count,
                                "language": "en",
                                "search_query": query,
                            },
                            default_source="youtube",
                            default_platform="youtube",
                        )
                        normalized_records.append(norm)
                        if len(normalized_records) >= limit:
                            break

                except Exception as c_err:
                    logger.warning(f"Could not fetch comments for video {video_id}: {c_err}")

    except Exception as e:
        logger.error(f"YouTube Data API execution failed: {e}")

    return normalized_records


def collect_youtube_comments(
    queries: Optional[List[str]] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Main YouTube collection entrypoint.
    Checks environment for YOUTUBE_API_KEY. If unavailable, logs limitation without failing.
    """
    load_dotenv()
    logger.info(f"Starting YouTube collection (limit={limit})...")
    api_key = os.getenv("YOUTUBE_API_KEY", "").strip()

    query_list = queries or [
        "Google Photos AI search",
        "Ask Google Photos search",
        "Google Photos find old photos",
        "Google Photos search update",
    ]

    if not api_key:
        logger.warning(
            "YOUTUBE_API_KEY environment variable is not configured. "
            "YouTube collector interface is ready, but API credentials are required by YouTube to fetch comment threads. "
            "Skipping YouTube collection (0 records collected)."
        )
        return []

    records = collect_via_youtube_api(api_key, query_list, limit=limit)
    logger.info(f"YouTube collection completed. Collected {len(records)} records.")
    return records
