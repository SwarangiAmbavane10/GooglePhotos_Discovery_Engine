"""
Normalization Utility for Google Photos Discovery Engine.
Enforces the mandatory 12-column research schema, handles timestamp standardizations,
and preserves the exact raw text without modifications.
"""

import hashlib
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_FIELDS: List[str] = [
    "record_id",
    "source",
    "platform",
    "source_id",
    "url",
    "title",
    "author",
    "text",
    "published_at",
    "rating",
    "language",
    "search_query",
    "collected_at",
]


def format_iso_timestamp(dt_input: Any) -> str:
    """Safely converts various datetime representations to an ISO 8601 string with UTC indicator."""
    if not dt_input:
        return ""
    if isinstance(dt_input, datetime):
        if dt_input.tzinfo is None:
            dt_input = dt_input.replace(tzinfo=timezone.utc)
        return dt_input.isoformat()
    if isinstance(dt_input, (int, float)):
        try:
            return datetime.fromtimestamp(dt_input, tz=timezone.utc).isoformat()
        except Exception:
            return ""
    if isinstance(dt_input, str):
        cleaned = dt_input.strip()
        if not cleaned:
            return ""
        # Try common datetime formats
        for fmt in (
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%a, %d %b %Y %H:%M:%S %Z",
            "%a, %d %b %Y %H:%M:%S %z",
        ):
            try:
                dt = datetime.strptime(cleaned, fmt)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.isoformat()
            except ValueError:
                continue
        # Fallback to returning the original string if it looks like a valid date format
        return cleaned
    return str(dt_input)


def generate_record_id(source: str, source_id: Optional[str], text: Optional[str] = None) -> str:
    """
    Generates a deterministic record identifier based on source and source_id,
    or a hash of source + text if source_id is unavailable.
    """
    clean_source = source.lower().replace(" ", "_")
    if source_id and str(source_id).strip():
        clean_id = re.sub(r"[^\w\-]", "_", str(source_id).strip())
        return f"{clean_source}_{clean_id}"
    
    # Hash fallback
    text_content = (text or "").strip()
    hash_digest = hashlib.sha256(f"{clean_source}:{text_content}".encode("utf-8")).hexdigest()[:16]
    return f"{clean_source}_{hash_digest}"


def normalize_record(raw: Dict[str, Any], default_source: str = "unknown", default_platform: str = "web") -> Dict[str, Any]:
    """
    Normalizes a single record into the canonical 12-field schema.
    Preserves exact user text verbatim without modification or summarization.
    """
    source = str(raw.get("source") or default_source).strip()
    platform = str(raw.get("platform") or default_platform).strip()
    source_id = str(raw.get("source_id") or "").strip() if raw.get("source_id") is not None else ""
    url = str(raw.get("url") or "").strip()
    title = str(raw.get("title") or "").strip()
    author = str(raw.get("author") or "").strip()
    
    # Preserve original raw text completely intact
    raw_text = raw.get("text")
    if raw_text is None:
        text = ""
    elif isinstance(raw_text, str):
        text = raw_text
    else:
        text = str(raw_text)

    # Published at
    published_at = format_iso_timestamp(raw.get("published_at"))
    
    # Rating: ensure string/number or empty string
    rating_val = raw.get("rating")
    if rating_val is not None and str(rating_val).strip() != "":
        try:
            rating = str(float(rating_val) if float(rating_val) != int(float(rating_val)) else int(float(rating_val)))
        except (ValueError, TypeError):
            rating = str(rating_val).strip()
    else:
        rating = ""

    language = str(raw.get("language") or "en").strip()
    search_query = str(raw.get("search_query") or "").strip()

    # Collected at
    collected_at = format_iso_timestamp(raw.get("collected_at") or datetime.now(timezone.utc))

    # Record ID
    record_id = raw.get("record_id")
    if not record_id or not str(record_id).strip():
        record_id = generate_record_id(source, source_id, text)
    else:
        record_id = str(record_id).strip()

    normalized: Dict[str, Any] = {
        "record_id": record_id,
        "source": source,
        "platform": platform,
        "source_id": source_id,
        "url": url,
        "title": title,
        "author": author,
        "text": text,
        "published_at": published_at,
        "rating": rating,
        "language": language,
        "search_query": search_query,
        "collected_at": collected_at,
    }

    return normalized


def validate_record(record: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validates that a normalized record conforms to schema requirements."""
    errors: List[str] = []
    
    # Check all fields exist
    for field in SCHEMA_FIELDS:
        if field not in record:
            errors.append(f"Missing schema field: '{field}'")

    if not record.get("record_id"):
        errors.append("Empty record_id")
    if not record.get("source"):
        errors.append("Empty source")
    if not record.get("text") and not record.get("title"):
        errors.append("Record contains neither text nor title")

    return (len(errors) == 0, errors)
