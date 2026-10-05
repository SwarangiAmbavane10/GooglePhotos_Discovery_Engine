"""
Main Orchestration Pipeline for Google Photos Discovery Engine Data Collection.

Coordinates:
  1. Source Discovery & Multi-Source Collection
  2. Strict Schema Normalization (12 mandatory columns)
  3. Source-specific raw exports & Timestamped Archiving
  4. Global Raw aggregation (scrape_data/raw/all_sources_raw.csv)
  5. Multi-tiered Deduplication (scrape_data/cleaned/all_sources_deduplicated.csv)
  6. Quality Checks & Collection Summary (scrape_data/collection_summary.csv)
  7. Audit Logging (scrape_data/collection_log.csv)
"""

import argparse
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
from dotenv import load_dotenv

# Import utilities
from utils.deduplication import deduplicate_records
from utils.logging_utils import (
    append_to_collection_log,
    archive_existing_file,
    calculate_source_metrics,
    ensure_directories,
    print_terminal_summary,
    save_records_to_csv,
    write_collection_summary,
)
from utils.normalization import SCHEMA_FIELDS, normalize_record, validate_record

# Import collectors
from collectors.app_store import collect_app_store_reviews
from collectors.forums import collect_forum_discussions
from collectors.google_photos_community import collect_google_photos_community
from collectors.google_play import collect_google_play_reviews
from collectors.reddit import collect_reddit_posts
from collectors.social_media import collect_social_media_posts
from collectors.youtube import collect_youtube_comments

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("DiscoveryEnginePipeline")


def load_search_config(config_path: Path) -> Dict[str, Any]:
    """Loads search terms and configuration from YAML."""
    if not config_path.exists():
        logger.warning(f"Config file not found at {config_path}. Using fallback query set.")
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def run_pipeline(
    base_dir: Path,
    limit_per_source: int = 35,
    selected_source: Optional[str] = None,
    is_test_mode: bool = False,
) -> Dict[str, Any]:
    """
    Executes the end-to-end data collection pipeline.
    """
    load_dotenv(base_dir / ".env")
    run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    logger.info(f"Starting Data Collection Pipeline (Run ID: {run_id}, Test Mode: {is_test_mode}, Limit: {limit_per_source})...")

    # 1. Ensure Directories
    dirs = ensure_directories(base_dir)
    config_file = base_dir / "config" / "search_queries.yaml"
    config = load_search_config(config_file)
    general_queries = config.get("google_photos_retrieval", [])
    source_cfg = config.get("source_specific", {})

    # 2. Collector Registry
    collectors_map = {
        "google_play": {
            "name": "Google Play Store",
            "func": lambda lim: collect_google_play_reviews(
                queries=source_cfg.get("google_play", {}).get("keywords", general_queries),
                limit=lim,
            ),
            "dir": dirs["google_play"],
        },
        "app_store": {
            "name": "Apple App Store",
            "func": lambda lim: collect_app_store_reviews(
                queries=source_cfg.get("app_store", {}).get("keywords", general_queries),
                limit=lim,
            ),
            "dir": dirs["app_store"],
        },
        "reddit": {
            "name": "Reddit",
            "func": lambda lim: collect_reddit_posts(
                queries=source_cfg.get("reddit", {}).get("queries", general_queries),
                subreddits=source_cfg.get("reddit", {}).get("subreddits", ["googlephotos", "google", "android"]),
                limit=lim,
            ),
            "dir": dirs["reddit"],
        },
        "google_photos_community": {
            "name": "Google Photos Help Community",
            "func": lambda lim: collect_google_photos_community(
                queries=source_cfg.get("google_photos_community", {}).get("queries", general_queries),
                limit=lim,
            ),
            "dir": dirs["google_photos_community"],
        },
        "youtube": {
            "name": "YouTube Comments",
            "func": lambda lim: collect_youtube_comments(
                queries=source_cfg.get("youtube", {}).get("queries", general_queries),
                limit=lim,
            ),
            "dir": dirs["youtube"],
        },
        "forums": {
            "name": "Public Forums (Hacker News & Tech)",
            "func": lambda lim: collect_forum_discussions(
                queries=source_cfg.get("forums", {}).get("queries", general_queries),
                limit=lim,
            ),
            "dir": dirs["forums"],
        },
        "social_media": {
            "name": "Public Social Media (Bluesky & Mastodon)",
            "func": lambda lim: collect_social_media_posts(
                queries=source_cfg.get("social_media", {}).get("queries", general_queries),
                limit=lim,
            ),
            "dir": dirs["social_media"],
        },
    }

    all_collected_raw_records: List[Dict[str, Any]] = []
    metrics_summary_list: List[Dict[str, Any]] = []
    sources_to_run = [selected_source] if selected_source else list(collectors_map.keys())

    date_tag = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 3. Execute Collectors Individually
    for src_key in sources_to_run:
        if src_key not in collectors_map:
            logger.warning(f"Unknown source '{src_key}'. Skipping.")
            continue

        c_info = collectors_map[src_key]
        src_name = c_info["name"]
        src_dir = c_info["dir"]
        collector_fn = c_info["func"]

        started_at = datetime.now(timezone.utc).isoformat()
        status = "SUCCESS"
        error_msg = ""
        source_records: List[Dict[str, Any]] = []

        logger.info(f"--- Running Collector: {src_name} ---")

        try:
            raw_data = collector_fn(limit_per_source)
            
            # Validate and collect records
            for r in raw_data:
                is_valid, errors = validate_record(r)
                if is_valid:
                    source_records.append(r)
                else:
                    logger.warning(f"Record validation failed for source {src_key}: {errors}")

        except Exception as e:
            status = "FAILED"
            error_msg = str(e)
            logger.error(f"Collector {src_name} failed with error: {e}", exc_info=True)

        finished_at = datetime.now(timezone.utc).isoformat()

        # Archive previous source file if it exists
        dated_file = src_dir / f"{src_key}_{date_tag}.csv"
        archive_existing_file(dated_file, dirs["archive"], src_key)

        # Save this source's raw CSV
        save_records_to_csv(source_records, dated_file)

        # Source deduplication check
        src_deduped, src_dupes = deduplicate_records(source_records)

        # Calculate metrics & Log entry
        metrics = calculate_source_metrics(source_records, src_name, duplicate_count=src_dupes)
        metrics_summary_list.append(metrics)

        used_queries = ", ".join(source_cfg.get(src_key, {}).get("queries", general_queries)[:3])
        log_entry = {
            "run_id": run_id,
            "source": src_key,
            "started_at": started_at,
            "finished_at": finished_at,
            "records_collected": len(source_records),
            "records_after_deduplication": len(src_deduped),
            "status": status if (len(source_records) > 0 or status == "SUCCESS") else "NO_RECORDS_OR_AUTH_REQUIRED",
            "error_message": error_msg,
            "queries_used": used_queries,
        }
        append_to_collection_log(base_dir / "scrape_data" / "collection_log.csv", log_entry)

        all_collected_raw_records.extend(source_records)

    # 4. Save Combined Raw Records (Preserving all sources when running full multi-source pipeline)
    if not selected_source:
        all_raw_file = dirs["raw"] / "all_sources_raw.csv"
        archive_existing_file(all_raw_file, dirs["archive"], "all_sources_raw")
        save_records_to_csv(all_collected_raw_records, all_raw_file)

        # 5. Deduplicate Corpus
        deduplicated_corpus, total_dupes_removed = deduplicate_records(all_collected_raw_records)
        all_cleaned_file = dirs["cleaned"] / "all_sources_deduplicated.csv"
        archive_existing_file(all_cleaned_file, dirs["archive"], "all_sources_deduplicated")
        save_records_to_csv(deduplicated_corpus, all_cleaned_file)
    else:
        all_raw_file = dirs["raw"] / f"{selected_source}" / f"{selected_source}_{date_tag}.csv"
        all_cleaned_file = None
        deduplicated_corpus, total_dupes_removed = deduplicate_records(all_collected_raw_records)

    # 6. Write Quality Summary
    summary_file = base_dir / "scrape_data" / "collection_summary.csv"
    write_collection_summary(summary_file, metrics_summary_list)

    # 7. Print Terminal Summary
    print_terminal_summary(metrics_summary_list, len(deduplicated_corpus))

    logger.info(f"Pipeline completed successfully. All artifacts preserved in {base_dir / 'scrape_data'}.")

    return {
        "run_id": run_id,
        "total_raw": len(all_collected_raw_records),
        "total_deduplicated": len(deduplicated_corpus),
        "summary_file": summary_file,
        "raw_file": all_raw_file,
        "cleaned_file": all_cleaned_file,
        "metrics": metrics_summary_list,
    }


def main():
    parser = argparse.ArgumentParser(description="Google Photos Discovery Engine - Data Collection Layer")
    parser.add_argument("--test", action="store_true", help="Run in test mode with small batch (20-40 records per source)")
    parser.add_argument("--limit", type=int, default=None, help="Explicit record limit per source")
    parser.add_argument("--source", type=str, default=None, help="Run only a specific source (google_play, app_store, reddit, etc.)")
    parser.add_argument("--full", action="store_true", help="Run full-scale collection (e.g. 200+ per source)")

    args = parser.parse_args()

    base_dir = Path(__file__).resolve().parent

    if args.limit:
        limit = args.limit
    elif args.test:
        limit = 35
    elif args.full:
        limit = 200
    else:
        # Default to small test batch per research requirement
        limit = 35

    run_pipeline(
        base_dir=base_dir,
        limit_per_source=limit,
        selected_source=args.source,
        is_test_mode=args.test or (not args.full and not args.limit),
    )


if __name__ == "__main__":
    main()
