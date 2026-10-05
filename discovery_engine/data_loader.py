"""
Google Photos Discovery Engine - Data Loader Module
===================================================
A safe, read-only data loader that accesses the processed datasets from
`Scrape_data/cleaned/` without modifying, overwriting, or mutating any files.

Expected datasets:
- all_sources_deduplicated.csv
- retrieval_relevance_classified.csv
- retrieval_evidence.csv
- retrieval_relevance_summary.csv (optional summary)
"""

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import pandas as pd
import logging

# Set up logger for data loader
logger = logging.getLogger("discovery_engine.data_loader")
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

# ---------------------------------------------------------------------------
# Path Resolution
# ---------------------------------------------------------------------------
def get_project_root() -> Path:
    """
    Dynamically resolves the project root directory relative to this file.
    Assumes `data_loader.py` is located in `discovery_engine/` or project root.
    """
    current_file = Path(__file__).resolve()
    # If in discovery_engine subdir: parent is project root
    if current_file.parent.name == "discovery_engine":
        return current_file.parent.parent
    # Fallback: parent directory
    return current_file.parent


def get_data_dir() -> Path:
    """
    Returns the Path to the processed clean data directory: `Scrape_data/cleaned`.
    """
    return get_project_root() / "Scrape_data" / "cleaned"


# File Constants
FILE_DEDUPLICATED = "all_sources_deduplicated.csv"
FILE_CLASSIFIED = "retrieval_relevance_classified.csv"
FILE_EVIDENCE = "retrieval_evidence.csv"
FILE_SUMMARY = "retrieval_relevance_summary.csv"

# Target evidence fields to verify
EXPECTED_EVIDENCE_FIELDS: List[str] = [
    "retrieval_scenario",
    "remembered_clues",
    "forgotten_or_unknown_clues",
    "search_behavior",
    "search_query_or_words_used",
    "failure_stage",
    "retrieval_barrier",
    "workaround",
    "retrieval_outcome",
    "evidence_quote",
    "evidence_strength",
]


class DataFileNotFoundError(FileNotFoundError):
    """Raised when a required dataset CSV file is missing from Scrape_data/cleaned/."""
    pass


# ---------------------------------------------------------------------------
# File Validation & Safe Loading
# ---------------------------------------------------------------------------
def check_data_files() -> Dict[str, Dict[str, Any]]:
    """
    Validates whether expected dataset files exist in Scrape_data/cleaned/.

    Returns:
        Dict mapping file identifier to status dict:
        {
            "filename": str,
            "path": Path,
            "exists": bool,
            "size_bytes": int or None,
            "error": str or None
        }
    """
    data_dir = get_data_dir()
    expected = {
        "deduplicated": FILE_DEDUPLICATED,
        "classified": FILE_CLASSIFIED,
        "evidence": FILE_EVIDENCE,
        "summary": FILE_SUMMARY,
    }

    status: Dict[str, Dict[str, Any]] = {}
    for key, fname in expected.items():
        file_path = data_dir / fname
        if file_path.is_file():
            try:
                size = file_path.stat().st_size
                status[key] = {
                    "filename": fname,
                    "path": file_path,
                    "exists": True,
                    "size_bytes": size,
                    "error": None,
                }
            except Exception as e:
                status[key] = {
                    "filename": fname,
                    "path": file_path,
                    "exists": True,
                    "size_bytes": None,
                    "error": str(e),
                }
        else:
            status[key] = {
                "filename": fname,
                "path": file_path,
                "exists": False,
                "size_bytes": None,
                "error": f"File not found at: {file_path}",
            }
    return status


def _safe_read_csv(file_name: str) -> pd.DataFrame:
    """
    Internal helper to safely read a CSV from Scrape_data/cleaned/.
    Preserves original data and returns an isolated copy.
    """
    data_dir = get_data_dir()
    file_path = data_dir / file_name

    if not file_path.is_file():
        err_msg = (
            f"Missing required dataset: '{file_name}'. "
            f"Expected location: {file_path.resolve()}"
        )
        logger.error(err_msg)
        raise DataFileNotFoundError(err_msg)

    try:
        df = pd.read_csv(file_path, low_memory=False)
        return df.copy()
    except Exception as e:
        err_msg = f"Failed to read dataset '{file_name}' at {file_path}: {e}"
        logger.error(err_msg)
        raise RuntimeError(err_msg) from e


def load_deduplicated_data() -> pd.DataFrame:
    """
    Loads all deduplicated records from all_sources_deduplicated.csv.
    """
    return _safe_read_csv(FILE_DEDUPLICATED)


def load_classified_data() -> pd.DataFrame:
    """
    Loads classified relevance records from retrieval_relevance_classified.csv.
    """
    return _safe_read_csv(FILE_CLASSIFIED)


def load_evidence_data() -> pd.DataFrame:
    """
    Loads extracted retrieval evidence records from retrieval_evidence.csv.
    """
    return _safe_read_csv(FILE_EVIDENCE)


def load_all_datasets() -> Dict[str, Union[pd.DataFrame, None]]:
    """
    Loads all core processed datasets.
    Returns a dictionary of dataframes keyed by dataset name.
    If a dataset cannot be loaded, its value is set to None.
    """
    datasets: Dict[str, Union[pd.DataFrame, None]] = {}

    for key, loader in [
        ("deduplicated", load_deduplicated_data),
        ("classified", load_classified_data),
        ("evidence", load_evidence_data),
    ]:
        try:
            datasets[key] = loader()
        except Exception as e:
            logger.warning(f"Could not load dataset '{key}': {e}")
            datasets[key] = None

    return datasets


# ---------------------------------------------------------------------------
# Metrics & Overview Calculations
# ---------------------------------------------------------------------------
def compute_overview_metrics(
    dedup_df: Optional[pd.DataFrame] = None,
    classified_df: Optional[pd.DataFrame] = None,
    evidence_df: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    """
    Calculates verified overview metrics strictly derived from the loaded datasets.
    Does NOT invent, interpolate, or guess any missing values.
    Returns 'Not available' for any metric that cannot be computed.
    """
    # Load if not passed
    if dedup_df is None:
        try:
            dedup_df = load_deduplicated_data()
        except Exception:
            dedup_df = None

    if classified_df is None:
        try:
            classified_df = load_classified_data()
        except Exception:
            classified_df = None

    if evidence_df is None:
        try:
            evidence_df = load_evidence_data()
        except Exception:
            evidence_df = None

    # 1. Total deduplicated records
    total_deduplicated: Any = "Not available"
    if dedup_df is not None:
        total_deduplicated = len(dedup_df)
    elif classified_df is not None:
        total_deduplicated = len(classified_df)

    # 2. Relevance labels from classified dataset
    total_relevant: Any = "Not available"
    highly_relevant: Any = "Not available"
    possibly_relevant: Any = "Not available"
    not_relevant: Any = "Not available"

    if classified_df is not None and "relevance_label" in classified_df.columns:
        counts = classified_df["relevance_label"].value_counts()
        highly_count = int(counts.get("highly_relevant", 0))
        possibly_count = int(counts.get("possibly_relevant", 0))
        not_relevant_count = int(counts.get("not_relevant", 0))

        highly_relevant = highly_count
        possibly_relevant = possibly_count
        not_relevant = not_relevant_count
        total_relevant = highly_count + possibly_count
    elif evidence_df is not None:
        # Evidence DF only contains relevant records
        total_relevant = len(evidence_df)
        if "relevance_label" in evidence_df.columns:
            counts = evidence_df["relevance_label"].value_counts()
            highly_relevant = int(counts.get("highly_relevant", 0))
            possibly_relevant = int(counts.get("possibly_relevant", 0))

    # 3. Number of source platforms / sources
    source_platforms_count: Any = "Not available"
    unique_sources: List[str] = []
    unique_platforms: List[str] = []

    active_df = dedup_df if dedup_df is not None else classified_df
    if active_df is not None:
        if "platform" in active_df.columns:
            unique_platforms = [str(p) for p in active_df["platform"].dropna().unique().tolist()]
        if "source" in active_df.columns:
            unique_sources = [str(s) for s in active_df["source"].dropna().unique().tolist()]

        if unique_platforms:
            source_platforms_count = len(unique_platforms)
        elif unique_sources:
            source_platforms_count = len(unique_sources)

    # 4. Number of records in retrieval_evidence.csv
    evidence_records_count: Any = "Not available"
    if evidence_df is not None:
        evidence_records_count = len(evidence_df)

    return {
        "total_deduplicated": total_deduplicated,
        "total_relevant": total_relevant,
        "highly_relevant": highly_relevant,
        "possibly_relevant": possibly_relevant,
        "not_relevant": not_relevant,
        "source_platforms_count": source_platforms_count,
        "evidence_records_count": evidence_records_count,
        "unique_sources": unique_sources,
        "unique_platforms": unique_platforms,
    }


# ---------------------------------------------------------------------------
# Data Sources Breakdown
# ---------------------------------------------------------------------------
def get_data_sources_summary(
    df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Returns a dataframe summarizing actual source and platform values found in the dataset.
    """
    if df is None:
        try:
            df = load_deduplicated_data()
        except Exception:
            try:
                df = load_classified_data()
            except Exception:
                return pd.DataFrame(columns=["source", "platform", "record_count"])

    if "source" not in df.columns or "platform" not in df.columns:
        cols_present = [c for c in ["source", "platform"] if c in df.columns]
        if not cols_present:
            return pd.DataFrame()
        summary = (
            df.groupby(cols_present)
            .size()
            .reset_index(name="record_count")
            .sort_values(by="record_count", ascending=False)
        )
        return summary

    summary = (
        df.groupby(["source", "platform"])
        .size()
        .reset_index(name="record_count")
        .sort_values(by="record_count", ascending=False)
    )
    return summary


# ---------------------------------------------------------------------------
# Evidence Coverage Check
# ---------------------------------------------------------------------------
def evaluate_evidence_coverage(
    evidence_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Evaluates presence and population coverage for required evidence fields.
    Does NOT infer or generate new values.
    """
    if evidence_df is None:
        try:
            evidence_df = load_evidence_data()
        except Exception:
            try:
                evidence_df = load_classified_data()
            except Exception:
                evidence_df = None

    rows: List[Dict[str, Any]] = []
    total_records = len(evidence_df) if evidence_df is not None else 0

    for field in EXPECTED_EVIDENCE_FIELDS:
        if evidence_df is None:
            rows.append({
                "field_name": field,
                "field_exists": False,
                "status": "Dataset Not Loaded",
                "populated_count": "Not available",
                "coverage_pct": "Not available",
            })
            continue

        exists = field in evidence_df.columns
        if not exists:
            rows.append({
                "field_name": field,
                "field_exists": False,
                "status": "Missing Field",
                "populated_count": 0,
                "coverage_pct": "0.0%",
            })
        else:
            populated = (
                evidence_df[field].fillna("").astype(str).str.strip() != ""
            ).sum()
            pct = (populated / total_records * 100) if total_records > 0 else 0.0
            rows.append({
                "field_name": field,
                "field_exists": True,
                "status": "Present",
                "populated_count": int(populated),
                "total_records": total_records,
                "coverage_pct": f"{pct:.1f}%",
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Platform Distribution
# ---------------------------------------------------------------------------
PLATFORM_DISPLAY_NAMES: Dict[str, str] = {
    "android": "Android",
    "ios": "iOS",
    "reddit": "Reddit",
    "google_help": "Google Help",
    "youtube": "YouTube",
    "hacker_news": "Hacker News",
    "lemmy_social": "Lemmy Social",
}


def get_platform_distribution(
    dedup_df: Optional[pd.DataFrame] = None,
    evidence_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Returns a unified distribution DataFrame across the seven verified platforms.
    """
    if dedup_df is None:
        try:
            dedup_df = load_deduplicated_data()
        except Exception:
            dedup_df = None

    if evidence_df is None:
        try:
            evidence_df = load_evidence_data()
        except Exception:
            evidence_df = None

    total_dedup = len(dedup_df) if dedup_df is not None else 0
    total_evidence = len(evidence_df) if evidence_df is not None else 0

    rows: List[Dict[str, Any]] = []
    for platform_key, platform_name in PLATFORM_DISPLAY_NAMES.items():
        dedup_count = 0
        if dedup_df is not None and "platform" in dedup_df.columns:
            dedup_count = int((dedup_df["platform"] == platform_key).sum())

        evidence_count = 0
        if evidence_df is not None and "platform" in evidence_df.columns:
            evidence_count = int((evidence_df["platform"] == platform_key).sum())

        dedup_pct = (dedup_count / total_dedup * 100) if total_dedup > 0 else 0.0
        evidence_pct = (evidence_count / total_evidence * 100) if total_evidence > 0 else 0.0

        rows.append({
            "platform_key": platform_key,
            "platform_name": platform_name,
            "dedup_count": dedup_count,
            "dedup_pct": dedup_pct,
            "evidence_count": evidence_count,
            "evidence_pct": evidence_pct,
        })

    return pd.DataFrame(rows)

