"""
Reddit Collector for Google Photos.
Collects public posts and comments discussing photo retrieval, search bugs, Ask Photos, and workarounds.
Supports PRAW (if credentials exist), public Reddit RSS search feeds, and public Reddit JSON endpoints with rate limiting.
"""

import html
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional
import feedparser
import requests
from utils.normalization import normalize_record

logger = logging.getLogger(__name__)


def collect_via_praw(
    client_id: str,
    client_secret: str,
    user_agent: str,
    subreddits: List[str],
    queries: List[str],
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Collects Reddit posts using PRAW with authorized credentials."""
    import praw

    normalized_records: List[Dict[str, Any]] = []
    try:
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )
        
        per_query_limit = max(5, limit // (len(queries) * len(subreddits) or 1))

        for sub_name in subreddits:
            subreddit = reddit.subreddit(sub_name)
            for query in queries:
                if len(normalized_records) >= limit:
                    break
                try:
                    for submission in subreddit.search(query, sort="relevance", limit=per_query_limit):
                        norm = normalize_record(
                            raw={
                                "source": "reddit",
                                "platform": "reddit",
                                "source_id": submission.id,
                                "url": f"https://www.reddit.com{submission.permalink}",
                                "title": submission.title,
                                "author": str(submission.author) if submission.author else "[deleted]",
                                "text": submission.selftext or submission.title,
                                "published_at": submission.created_utc,
                                "rating": submission.score,
                                "language": "en",
                                "search_query": query,
                            },
                            default_source="reddit",
                            default_platform="reddit",
                        )
                        normalized_records.append(norm)
                        if len(normalized_records) >= limit:
                            break
                except Exception as e:
                    logger.warning(f"PRAW search failed for '{query}' in r/{sub_name}: {e}")

    except Exception as e:
        logger.error(f"PRAW initialization or collection failed: {e}")

    return normalized_records


def clean_html_snippet(raw_html: str) -> str:
    """Strips HTML tags from Reddit RSS summary text."""
    if not raw_html:
        return ""
    # Unescape HTML entities
    unescaped = html.unescape(raw_html)
    # Remove HTML tags
    cleaned = re.sub(r"<[^>]+>", " ", unescaped)
    return re.sub(r"\s+", " ", cleaned).strip()


def collect_via_reddit_rss(
    subreddits: List[str],
    queries: List[str],
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Collects real Reddit posts via public Reddit search RSS feeds.
    Completely public, requires no login, and respects Reddit server capacity.
    """
    normalized_records: List[Dict[str, Any]] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    seen_ids = set()

    for sub in subreddits:
        if len(normalized_records) >= limit:
            break

        for q in queries:
            if len(normalized_records) >= limit:
                break

            url = f"https://www.reddit.com/r/{sub}/search.rss"
            params = {
                "q": q,
                "restrict_sr": "1",
                "sort": "relevance",
            }

            try:
                resp = requests.get(url, headers=headers, params=params, timeout=12)
                if resp.status_code == 200:
                    feed = feedparser.parse(resp.content)
                    for entry in feed.entries:
                        entry_id = entry.get("id", "") or entry.get("link", "")
                        # Extract post ID from link or ID
                        id_match = re.search(r"/comments/([a-z0-9]+)/", entry.get("link", ""))
                        post_id = id_match.group(1) if id_match else entry_id

                        if not post_id or post_id in seen_ids:
                            continue
                        seen_ids.add(post_id)

                        title = entry.get("title", "")
                        raw_summary = entry.get("summary", "")
                        text = clean_html_snippet(raw_summary) or title
                        author = entry.get("author", "Reddit User").replace("/u/", "")
                        link = entry.get("link", "")
                        published = entry.get("updated", "") or entry.get("published", "")

                        norm = normalize_record(
                            raw={
                                "source": "reddit",
                                "platform": "reddit",
                                "source_id": post_id,
                                "url": link,
                                "title": title,
                                "author": author,
                                "text": text,
                                "published_at": published,
                                "rating": "",
                                "language": "en",
                                "search_query": q,
                            },
                            default_source="reddit",
                            default_platform="reddit",
                        )
                        normalized_records.append(norm)

                        if len(normalized_records) >= limit:
                            break

                time.sleep(1.0)  # Gentle spacing between query feeds
            except Exception as e:
                logger.warning(f"Error fetching Reddit RSS for r/{sub} query '{q}': {e}")

    # Fallback to new.rss if needed to reach limit
    if len(normalized_records) < limit:
        for sub in subreddits:
            if len(normalized_records) >= limit:
                break
            try:
                resp = requests.get(f"https://www.reddit.com/r/{sub}/new.rss", headers=headers, timeout=12)
                if resp.status_code == 200:
                    feed = feedparser.parse(resp.content)
                    for entry in feed.entries:
                        link = entry.get("link", "")
                        id_match = re.search(r"/comments/([a-z0-9]+)/", link)
                        post_id = id_match.group(1) if id_match else entry.get("id", "")
                        if not post_id or post_id in seen_ids:
                            continue
                        seen_ids.add(post_id)

                        title = entry.get("title", "")
                        text = clean_html_snippet(entry.get("summary", "")) or title
                        author = entry.get("author", "Reddit User").replace("/u/", "")
                        published = entry.get("updated", "") or entry.get("published", "")

                        norm = normalize_record(
                            raw={
                                "source": "reddit",
                                "platform": "reddit",
                                "source_id": post_id,
                                "url": link,
                                "title": title,
                                "author": author,
                                "text": text,
                                "published_at": published,
                                "rating": "",
                                "language": "en",
                                "search_query": "subreddit_recent",
                            },
                            default_source="reddit",
                            default_platform="reddit",
                        )
                        normalized_records.append(norm)
                        if len(normalized_records) >= limit:
                            break
            except Exception as e:
                logger.warning(f"Error fetching Reddit new.rss for r/{sub}: {e}")

    return normalized_records


def collect_reddit_posts(
    queries: Optional[List[str]] = None,
    subreddits: Optional[List[str]] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """
    Main Reddit collection dispatcher. Checks for PRAW credentials in environment,
    falling back seamlessly to public Reddit search RSS feeds.
    """
    logger.info(f"Starting Reddit collection (limit={limit})...")
    
    sub_list = subreddits or ["googlephotos", "google", "android"]
    query_list = queries or [
        "can't find photo",
        "search doesn't work",
        "search old photos",
        "Ask Photos",
        "find specific photo",
    ]

    client_id = os.getenv("REDDIT_CLIENT_ID", "").strip()
    client_secret = os.getenv("REDDIT_CLIENT_SECRET", "").strip()
    user_agent = os.getenv("REDDIT_USER_AGENT", "").strip()

    if client_id and client_secret:
        logger.info("Using PRAW with configured Reddit OAuth credentials.")
        records = collect_via_praw(client_id, client_secret, user_agent, sub_list, query_list, limit=limit)
    else:
        logger.info("Reddit credentials not configured; using public Reddit RSS search feeds with rate limiting.")
        records = collect_via_reddit_rss(sub_list, query_list, limit=limit)

    logger.info(f"Reddit collection completed. Collected {len(records)} records.")
    return records
