"""
Logging and Archiving Utilities for Google Photos Discovery Engine.
Handles run logging, quality metrics calculation, summary export,
and timestamped archival preservation.
"""

import csv
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from utils.normalization import SCHEMA_FIELDS

LOG_COLUMNS = [
    "run_id",
    "source",
    "started_at",
    "finished_at",
    "records_collected",
    "records_after_deduplication",
    "status",
    "error_message",
    "queries_used",
]

SUMMARY_COLUMNS = [
    "source",
    "records_collected",
    "records_with_text",
    "records_with_url",
    "records_with_date",
    "duplicate_count",
    "empty_record_count",
]


def ensure_directories(base_dir: Path) -> Dict[str, Path]:
    """Ensures all standard project directories exist and returns a dictionary of paths."""
    dirs = {
        "scrape_data": base_dir / "scrape_data",
        "raw": base_dir / "scrape_data" / "raw",
        "cleaned": base_dir / "scrape_data" / "cleaned",
        "archive": base_dir / "scrape_data" / "archive",
        "google_play": base_dir / "scrape_data" / "raw" / "google_play",
        "app_store": base_dir / "scrape_data" / "raw" / "app_store",
        "reddit": base_dir / "scrape_data" / "raw" / "reddit",
        "google_photos_community": base_dir / "scrape_data" / "raw" / "google_photos_community",
        "youtube": base_dir / "scrape_data" / "raw" / "youtube",
        "forums": base_dir / "scrape_data" / "raw" / "forums",
        "social_media": base_dir / "scrape_data" / "raw" / "social_media",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def save_records_to_csv(records: List[Dict[str, Any]], filepath: Path) -> None:
    """Writes a list of normalized records to a CSV file with full field safety."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    with open(filepath, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SCHEMA_FIELDS, extrasaction="ignore", quoting=csv.QUOTE_MINIMAL)
        writer.writeheader()
        for record in records:
            writer.writerow(record)


def archive_existing_file(filepath: Path, archive_dir: Path, source_name: str) -> Optional[Path]:
    """Archives an existing raw file by adding a timestamp to avoid overwriting raw evidence."""
    if not filepath.exists() or filepath.stat().st_size == 0:
        return None
    archive_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H%M%S")
    archive_path = archive_dir / f"{source_name}_{date_str}.csv"
    shutil.copy2(filepath, archive_path)
    return archive_path


def append_to_collection_log(log_path: Path, log_entry: Dict[str, Any]) -> None:
    """Appends an execution log record to scrape_data/collection_log.csv."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = log_path.exists() and log_path.stat().st_size > 0

    with open(log_path, mode="a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=LOG_COLUMNS, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerow({col: log_entry.get(col, "") for col in LOG_COLUMNS})


def calculate_source_metrics(records: List[Dict[str, Any]], source_name: str, duplicate_count: int = 0) -> Dict[str, Any]:
    """Computes data quality and completeness metrics for a set of records."""
    total = len(records)
    records_with_text = sum(1 for r in records if bool(str(r.get("text") or "").strip()))
    records_with_url = sum(1 for r in records if bool(str(r.get("url") or "").strip()))
    records_with_date = sum(1 for r in records if bool(str(r.get("published_at") or "").strip()))
    empty_records = sum(1 for r in records if not str(r.get("text") or "").strip() and not str(r.get("title") or "").strip())

    return {
        "source": source_name,
        "records_collected": total,
        "records_with_text": records_with_text,
        "records_with_url": records_with_url,
        "records_with_date": records_with_date,
        "duplicate_count": duplicate_count,
        "empty_record_count": empty_records,
    }


def write_collection_summary(summary_path: Path, metrics_list: List[Dict[str, Any]]) -> None:
    """Writes the collection summary quality report to scrape_data/collection_summary.csv."""
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    with open(summary_path, mode="w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=SUMMARY_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        for metric in metrics_list:
            writer.writerow({col: metric.get(col, "") for col in SUMMARY_COLUMNS})


def print_terminal_summary(metrics_list: List[Dict[str, Any]], total_deduplicated: int) -> None:
    """Prints a clean, formatted terminal summary of the collection run."""
    print("\n" + "=" * 60)
    print("GOOGLE PHOTOS DISCOVERY ENGINE — DATA COLLECTION SUMMARY")
    print("=" * 60)
    print(f"{'SOURCE':<30} {'RECORDS':<12} {'DEDUP COUNT':<12}")
    print("-" * 60)

    total_collected = 0
    total_dupes = 0
    for m in metrics_list:
        source = m.get("source", "Unknown")
        collected = m.get("records_collected", 0)
        dupes = m.get("duplicate_count", 0)
        total_collected += collected
        total_dupes += dupes
        print(f"{source:<30} {collected:<12} {dupes:<12}")

    print("-" * 60)
    print(f"{'TOTAL RAW RECORDS':<30} {total_collected:<12}")
    print(f"{'TOTAL DEDUPLICATED':<30} {total_deduplicated:<12}")
    print("=" * 60 + "\n")
