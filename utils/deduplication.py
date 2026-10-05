"""
Deduplication Utility for Google Photos Discovery Engine.
Implements multi-tiered deduplication without altering original raw text or metadata.
"""

import hashlib
import re
from typing import Any, Dict, List, Set, Tuple


def normalize_text_for_comparison(text: str) -> str:
    """Normalizes text strictly for hash comparison (collapses whitespace, lowercases)."""
    if not text:
        return ""
    return re.sub(r"\s+", " ", text.strip().lower())


def get_text_hash(text: str) -> str:
    """Generates a SHA-256 hash of normalized text for exact/near-duplicate detection."""
    normalized = normalize_text_for_comparison(text)
    if not normalized:
        return ""
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def canonicalize_url(url: str) -> str:
    """Strips tracking parameters and trailing slashes for URL deduplication."""
    if not url:
        return ""
    clean_url = url.strip()
    # Strip common tracking query params
    clean_url = re.sub(r"([?&])(utm_[^&]+|ref=[^&]+|fbclid=[^&]+|gclid=[^&]+)", "", clean_url)
    clean_url = clean_url.rstrip("?&/").lower()
    return clean_url


def deduplicate_records(records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    """
    Deduplicates a list of normalized records using multi-tiered criteria:
      1. source + source_id (when source_id is non-empty)
      2. unique post/thread/comment canonical URL (when specific URL is present and source_id is absent)
      3. normalized text hash (for identical or near-identical substantive text content)

    Preserves the original record order and first-seen record integrity.
    Returns (deduplicated_records, duplicate_count).
    """
    deduplicated: List[Dict[str, Any]] = []
    seen_source_ids: Set[str] = set()
    seen_urls: Set[str] = set()
    seen_text_hashes: Set[str] = set()
    duplicate_count = 0

    for record in records:
        source = str(record.get("source") or "").strip().lower()
        source_id = str(record.get("source_id") or "").strip()
        url = str(record.get("url") or "").strip()
        text = str(record.get("text") or "").strip()
        title = str(record.get("title") or "").strip()

        combined_text = f"{title} {text}".strip()
        text_hash = get_text_hash(combined_text)
        canon_url = canonicalize_url(url)
        source_id_key = f"{source}:{source_id}" if (source and source_id) else ""

        is_duplicate = False

        # Tier 1: source + source_id match
        if source_id_key and source_id_key in seen_source_ids:
            is_duplicate = True

        # Tier 2: normalized text hash (for identical text content > 15 chars)
        elif text_hash and len(combined_text) > 15 and text_hash in seen_text_hashes:
            is_duplicate = True

        # Tier 3: canonical URL match (when source_id is not present to avoid collisions on base app URLs)
        elif not source_id_key and canon_url and canon_url in seen_urls:
            is_duplicate = True

        if is_duplicate:
            duplicate_count += 1
            continue

        # Register keys
        if source_id_key:
            seen_source_ids.add(source_id_key)
        if canon_url:
            seen_urls.add(canon_url)
        if text_hash and len(combined_text) > 15:
            seen_text_hashes.add(text_hash)

        deduplicated.append(record)

    return deduplicated, duplicate_count
