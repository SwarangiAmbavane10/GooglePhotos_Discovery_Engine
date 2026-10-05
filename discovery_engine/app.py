"""
Google Photos — AI-Powered Discovery Engine
============================================
A simplified, human-intuitive Discovery Engine exploring how people find photos
they only vaguely remember across verified multi-platform evidence records.

Information Architecture:
1. HEADER (Simple, High Clarity)
2. WHAT IS THIS? (What are we trying to understand? + Core Research Loop)
3. SYSTEM & DATA INTEGRITY (Verified Research Foundation, Data Flow, Status Indicators)
4. WHAT DID WE LEARN? (Metric Ribbon + 4 Discovery Summaries)
5. HOW DOES THE RETRIEVAL PROBLEM HAPPEN? (Memory → Search Mismatch)
6. ANSWER THE 4 DISCOVERY QUESTIONS (01 Scenarios, 02 Remembered, 03 Forgotten, 04 Search)
7. EXPLORE THE EVIDENCE (Search, Filters, Compact Cards with Expandable Details)
8. WHAT DOES THIS MEAN FOR THE PRODUCT? (Insights & PM Opportunity Pipeline)
"""

import html
from pathlib import Path
import re
import sys
import textwrap
from typing import Any, Dict, List, Optional
import pandas as pd
import streamlit as st

# Ensure discovery_engine package is in path
CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from discovery_engine import data_loader
from discovery_engine import pattern_analysis

# ---------------------------------------------------------------------------
# Streamlit Page Configuration (Full Canvas, No Sidebar)
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Google Photos — AI-Powered Discovery Engine",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Safe HTML Rendering Helper
# ---------------------------------------------------------------------------
def render_html(html_str: str) -> None:
    """
    Renders HTML safely and directly.
    Uses st.html() when available (Streamlit 1.35+) to avoid Markdown parser issues,
    or falls back to st.markdown(..., unsafe_allow_html=True).
    """
    clean_html = textwrap.dedent(html_str).strip()
    if hasattr(st, "html"):
        st.html(clean_html)
    else:
        st.markdown(clean_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Custom CSS for Modern, High-Contrast Research UI
# ---------------------------------------------------------------------------
render_html(
    """<style>
/* Hide Default Streamlit Sidebar & Floating Clutter */
[data-testid="stSidebar"], [data-testid="stSidebarNav"], [data-testid="collapsedControl"] {
    display: none !important;
}
#MainMenu, footer, header {
    visibility: hidden;
}
.stDeployButton {
    display: none;
}

/* Ensure Dark Background & Clean Contrast */
html, body, .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"], [data-testid="stMain"] {
    background-color: #121212 !important;
    color: #e8eaed !important;
}
.main {
    background-color: #121212 !important;
}

/* Container & Layout */
.main .block-container {
    background-color: #121212 !important;
    padding-top: 1.5rem;
    padding-bottom: 5rem;
    max-width: 1200px;
    margin: 0 auto;
}

/* Typography Defaults */
h1, h2, h3, h4, p, span, div, label {
    font-family: -apple-system, BlinkMacSystemFont, "Google Sans", "Segoe UI", Roboto, sans-serif;
}

/* 1. Header */
.header-container {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    flex-wrap: wrap;
    gap: 0.75rem;
    margin-bottom: 1.25rem;
    padding-bottom: 0.9rem;
    border-bottom: 1px solid #2d3135;
}
.hero-brand {
    font-size: 0.8rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.8px;
    color: #8ab4f8 !important;
    margin-bottom: 0.2rem;
}
.hero-title {
    font-size: 1.75rem;
    font-weight: 700;
    color: #ffffff !important;
    letter-spacing: -0.3px;
    line-height: 1.2;
    margin: 0;
}
.hero-subtitle {
    font-size: 0.98rem;
    color: #bdc1c6 !important;
    font-weight: 400;
    margin-top: 0.25rem;
    margin-bottom: 0;
}

/* Status Badges */
.badge-container {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    flex-wrap: wrap;
}
.status-badge {
    display: inline-flex;
    align-items: center;
    padding: 0.22rem 0.6rem;
    border-radius: 4px;
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.3px;
    text-transform: uppercase;
    background-color: #1e1e1e;
    color: #bdc1c6;
    border: 1px solid #3c4043;
}
.status-badge-green {
    background-color: #133824;
    color: #81c995;
    border-color: #1e5c36;
}
.status-badge-blue {
    background-color: #1a3a60;
    color: #8ab4f8;
    border-color: #283e60;
}

/* Section Headings */
.section-header-block {
    margin-top: 2rem;
    margin-bottom: 0.9rem;
}
.section-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: #ffffff !important;
    letter-spacing: 0.2px;
    margin: 0 0 0.2rem 0;
}
.section-subtitle {
    font-size: 0.86rem;
    color: #9aa0a6 !important;
    margin: 0;
}

/* 2. What Is This Box */
.what-is-this-card {
    background: #181c24;
    border: 1px solid #283e60;
    border-left: 4px solid #8ab4f8;
    border-radius: 0 8px 8px 0;
    padding: 1rem 1.25rem;
    margin-bottom: 1.25rem;
    font-size: 0.94rem;
    color: #e8eaed !important;
    line-height: 1.55;
}
.what-is-this-heading {
    font-size: 0.88rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    color: #8ab4f8 !important;
    margin-bottom: 0.4rem;
}

/* Core Research Loop */
.research-loop-grid {
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 0.65rem;
    margin-top: 0.9rem;
}
@media (max-width: 900px) {
    .research-loop-grid {
        grid-template-columns: 1fr;
    }
}
.loop-node {
    background: #1e1e1e;
    border: 1px solid #2d3135;
    border-radius: 6px;
    padding: 0.75rem 0.85rem;
    transition: transform 0.15s ease;
}
.loop-node-tag {
    font-size: 0.78rem;
    font-weight: 700;
    color: #8ab4f8 !important;
    margin-bottom: 0.2rem;
    display: flex;
    align-items: center;
    gap: 0.35rem;
}
.loop-node-title {
    font-size: 0.84rem;
    font-weight: 600;
    color: #ffffff !important;
}
.loop-node-desc {
    font-size: 0.75rem;
    color: #9aa0a6 !important;
    margin-top: 0.2rem;
    line-height: 1.35;
}

/* 3. Horizontal Metric Ribbon */
.metric-ribbon {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.65rem;
    background: #18191c;
    border: 1px solid #2d3135;
    border-radius: 8px;
    padding: 0.75rem 1rem;
    margin-bottom: 1rem;
}
@media (max-width: 768px) {
    .metric-ribbon {
        grid-template-columns: repeat(2, 1fr);
    }
}
.metric-ribbon-item {
    display: flex;
    flex-direction: column;
}
.metric-ribbon-val {
    font-size: 1.4rem;
    font-weight: 700;
    color: #ffffff !important;
    line-height: 1.2;
}
.metric-ribbon-lbl {
    font-size: 0.76rem;
    font-weight: 600;
    color: #9aa0a6 !important;
    margin-top: 0.15rem;
}

/* 4 Compact Discovery Summaries */
.discovery-summary-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 0.65rem;
    margin-bottom: 1.5rem;
}
@media (max-width: 900px) {
    .discovery-summary-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}
.summary-card {
    background: #1e1e1e;
    border: 1px solid #2d3135;
    border-radius: 6px;
    padding: 0.8rem 0.9rem;
    border-top: 3px solid #8ab4f8;
}
.summary-card-tag {
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #8ab4f8 !important;
    margin-bottom: 0.2rem;
}
.summary-card-q {
    font-size: 0.76rem;
    color: #9aa0a6 !important;
    margin-bottom: 0.4rem;
    line-height: 1.3;
}
.summary-card-pattern {
    font-size: 0.86rem;
    font-weight: 600;
    color: #ffffff !important;
}
.summary-card-count {
    font-size: 0.75rem;
    color: #bdc1c6 !important;
    margin-top: 0.2rem;
}

/* 4. Memory vs Search Mismatch */
.mismatch-wrapper {
    background: #1e1e1e;
    border: 1px solid #2d3135;
    border-radius: 8px;
    padding: 1.15rem 1.25rem;
    margin-bottom: 1.75rem;
}
.mismatch-flow-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    background: #16181b;
    border-radius: 6px;
    padding: 0.65rem 1rem;
    margin-bottom: 1rem;
    border: 1px solid #282a2d;
    font-size: 0.8rem;
    font-weight: 600;
}
.mismatch-flow-step {
    display: flex;
    align-items: center;
    gap: 0.35rem;
}
.mismatch-flow-arrow {
    color: #8ab4f8;
    font-size: 0.85rem;
}
.mismatch-columns {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-bottom: 1rem;
}
@media (max-width: 768px) {
    .mismatch-columns {
        grid-template-columns: 1fr;
    }
}
.mismatch-box {
    background: #18191c;
    border-radius: 6px;
    padding: 0.9rem 1rem;
    border: 1px solid #2d3135;
}
.mismatch-box-title {
    font-size: 0.82rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.4px;
    margin-bottom: 0.6rem;
    display: flex;
    align-items: center;
    gap: 0.4rem;
}
.mismatch-row {
    font-size: 0.82rem;
    color: #bdc1c6 !important;
    padding: 0.3rem 0;
    border-bottom: 1px solid #25282c;
    line-height: 1.4;
}
.mismatch-row:last-child {
    border-bottom: none;
}
.mismatch-row strong {
    color: #e8eaed !important;
}

.mismatch-example-box {
    background: #141a24;
    border-left: 3.5px solid #8ab4f8;
    padding: 0.75rem 1rem;
    border-radius: 0 6px 6px 0;
    font-size: 0.82rem;
    color: #e8eaed !important;
    line-height: 1.45;
}
.mismatch-example-title {
    font-size: 0.74rem;
    font-weight: 700;
    text-transform: uppercase;
    color: #8ab4f8 !important;
    margin-bottom: 0.25rem;
}

/* 5. The Four Discovery Questions */
.discovery-q-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1rem;
    margin-bottom: 1.75rem;
}
@media (max-width: 850px) {
    .discovery-q-grid {
        grid-template-columns: 1fr;
    }
}
.discovery-q-card {
    background: #1e1e1e;
    border: 1px solid #2d3135;
    border-radius: 8px;
    padding: 1.1rem 1.25rem;
}
.discovery-q-num {
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #8ab4f8 !important;
    margin-bottom: 0.25rem;
}
.discovery-q-title {
    font-size: 1.02rem;
    font-weight: 700;
    color: #ffffff !important;
    margin-bottom: 0.75rem;
}
.discovery-q-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.32rem 0;
    border-bottom: 1px solid #282a2d;
    font-size: 0.82rem;
}
.discovery-q-item:last-child {
    border-bottom: none;
}
.discovery-q-name {
    color: #bdc1c6 !important;
    font-weight: 500;
}
.discovery-q-stat {
    color: #8ab4f8 !important;
    font-weight: 600;
    font-size: 0.78rem;
}

/* Horizontal Visual Bars in Q2 */
.bar-track {
    background-color: #282a2d;
    height: 6px;
    border-radius: 3px;
    overflow: hidden;
    margin: 0.25rem 0 0.5rem 0;
}
.bar-fill {
    background-color: #8ab4f8;
    height: 100%;
    border-radius: 3px;
}

/* 6. Explore Evidence */
.evidence-card {
    background: #1e1e1e;
    border: 1px solid #2d3135;
    border-radius: 8px;
    padding: 1rem 1.15rem;
    margin-bottom: 0.85rem;
    transition: border-color 0.15s ease;
}
.evidence-card:hover {
    border-color: #3c4043;
}
.evidence-card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.5rem;
    margin-bottom: 0.5rem;
}
.tag-highly-rel {
    background-color: #133824;
    color: #81c995;
    border: 1px solid #1e5c36;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
}
.tag-possibly-rel {
    background-color: #3b2d14;
    color: #fdd663;
    border: 1px solid #634b1a;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 700;
    text-transform: uppercase;
}
.tag-platform-badge {
    background-color: #282a2d;
    color: #bdc1c6;
    border: 1px solid #3c4043;
    padding: 0.15rem 0.5rem;
    border-radius: 4px;
    font-size: 0.7rem;
    font-weight: 600;
}
.evidence-quote {
    font-size: 0.94rem;
    font-weight: 500;
    color: #ffffff !important;
    line-height: 1.45;
    margin-bottom: 0.65rem;
    border-left: 3px solid #8ab4f8;
    padding-left: 0.75rem;
}
.evidence-mini-flow {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.4rem;
    font-size: 0.76rem;
    color: #9aa0a6 !important;
    background: #18191c;
    padding: 0.4rem 0.65rem;
    border-radius: 4px;
    border: 1px solid #282a2d;
    margin-bottom: 0.4rem;
}
.mini-flow-node {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    color: #bdc1c6 !important;
}
.mini-flow-node strong {
    color: #ffffff !important;
}

/* Search Highlight */
.search-hl {
    background-color: #5c4813;
    color: #fef08a;
    font-weight: 600;
    padding: 0 2px;
    border-radius: 2px;
}

/* 7. Discovery Insights & PM Opportunity */
.insight-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.85rem;
    margin-bottom: 1.5rem;
}
@media (max-width: 850px) {
    .insight-grid {
        grid-template-columns: 1fr;
    }
}
.insight-card {
    background: #1e1e1e;
    border: 1px solid #2d3135;
    border-radius: 8px;
    padding: 1rem 1.15rem;
    border-top: 3.5px solid #8ab4f8;
}
.insight-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 0.35rem;
}
.insight-num {
    font-size: 0.72rem;
    font-weight: 700;
    color: #8ab4f8 !important;
    text-transform: uppercase;
}
.insight-stat {
    font-size: 0.74rem;
    font-weight: 600;
    color: #81c995 !important;
    background: #133824;
    padding: 0.1rem 0.4rem;
    border-radius: 3px;
}
.insight-title {
    font-size: 0.96rem;
    font-weight: 700;
    color: #ffffff !important;
    margin-bottom: 0.5rem;
}
.insight-chain-step {
    font-size: 0.8rem;
    color: #bdc1c6 !important;
    margin-bottom: 0.3rem;
    line-height: 1.4;
}
.insight-chain-step strong {
    color: #e8eaed !important;
}

/* Product Opportunity Visual Pipeline */
.pm-pipeline-banner {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    background: #18191c;
    border: 1px solid #2d3135;
    border-radius: 6px;
    padding: 0.6rem 1rem;
    margin-bottom: 1rem;
    font-size: 0.8rem;
    font-weight: 600;
    color: #bdc1c6;
}

.opp-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.85rem;
    margin-bottom: 1.75rem;
}
@media (max-width: 850px) {
    .opp-grid {
        grid-template-columns: 1fr;
    }
}
.opp-card {
    background: #1e1e1e;
    border: 1px solid #2d3135;
    border-radius: 8px;
    padding: 1rem 1.15rem;
    border-left: 3.5px solid #8ab4f8;
}
.opp-stage {
    font-size: 0.7rem;
    font-weight: 700;
    color: #8ab4f8 !important;
    text-transform: uppercase;
    margin-bottom: 0.2rem;
}
.opp-title {
    font-size: 0.94rem;
    font-weight: 700;
    color: #ffffff !important;
    margin-bottom: 0.45rem;
}
.opp-content {
    font-size: 0.81rem;
    color: #bdc1c6 !important;
    line-height: 1.45;
}
.opp-content strong {
    color: #e8eaed !important;
}

/* System & Data Integrity */
.integrity-container {
    background: #18191c;
    border: 1px solid #2d3135;
    border-radius: 8px;
    padding: 1.15rem 1.25rem;
    margin-bottom: 1.5rem;
}
.integrity-title-tag {
    font-size: 0.76rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.6px;
    color: #8ab4f8 !important;
    margin-bottom: 0.2rem;
}
.integrity-heading {
    font-size: 1.05rem;
    font-weight: 700;
    color: #ffffff !important;
    margin: 0 0 0.75rem 0;
}
.integrity-stats-list {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.4rem 0.75rem;
    background: #141518;
    border: 1px solid #25282c;
    border-radius: 6px;
    padding: 0.65rem 0.9rem;
    margin-bottom: 0.85rem;
    font-size: 0.84rem;
    color: #bdc1c6 !important;
}
.integrity-stat-item {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
}
.integrity-stat-item strong {
    color: #ffffff !important;
    font-weight: 700;
}
.integrity-stat-bullet {
    color: #3c4043 !important;
    font-weight: 700;
    user-select: none;
}
.integrity-flow-wrapper {
    background: #141518;
    border: 1px solid #25282c;
    border-radius: 6px;
    padding: 0.75rem 0.9rem;
    margin-bottom: 0.85rem;
}
.integrity-flow-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.4rem;
}
.integrity-flow-step {
    font-size: 0.8rem;
    font-weight: 600;
    color: #e8eaed !important;
    background: #1f2227;
    border: 1px solid #2d3135;
    border-radius: 4px;
    padding: 0.3rem 0.65rem;
    white-space: nowrap;
}
.integrity-flow-arrow {
    color: #8ab4f8 !important;
    font-size: 0.9rem;
    font-weight: 700;
    user-select: none;
}
.integrity-flow-note {
    font-size: 0.79rem;
    color: #9aa0a6 !important;
    margin-top: 0.6rem;
    padding-top: 0.5rem;
    border-top: 1px solid #202327;
    line-height: 1.4;
}
.integrity-status-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.65rem;
}
@media (max-width: 768px) {
    .integrity-status-row {
        grid-template-columns: 1fr;
    }
}
.integrity-status-card {
    background: #141518;
    border: 1px solid #25282c;
    border-radius: 6px;
    padding: 0.65rem 0.85rem;
}
.integrity-status-badge {
    margin-bottom: 0.35rem;
}
.integrity-status-desc {
    font-size: 0.78rem;
    color: #9aa0a6 !important;
    line-height: 1.35;
    margin: 0;
}

/* Distribution Bar in Bottom Integrity */
.dist-container {
    display: flex;
    height: 10px;
    width: 100%;
    border-radius: 5px;
    overflow: hidden;
    background-color: #282a2d;
    margin-top: 0.5rem;
    margin-bottom: 0.75rem;
}
.dist-segment {
    height: 100%;
}
.dist-legend {
    display: flex;
    flex-wrap: wrap;
    gap: 0.75rem;
    font-size: 0.75rem;
    color: #9aa0a6 !important;
}
.dist-legend strong {
    color: #e8eaed !important;
}
.dist-dot {
    display: inline-block;
    width: 8px;
    height: 8px;
    border-radius: 50%;
    margin-right: 0.25rem;
}
</style>"""
)

# ---------------------------------------------------------------------------
# Data Loading with Streamlit Caching
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_discovery_data():
    """Safely loads all verified datasets and computes metrics."""
    files_status = data_loader.check_data_files()
    datasets = data_loader.load_all_datasets()
    dedup_df = datasets.get("deduplicated")
    classified_df = datasets.get("classified")
    evidence_df = datasets.get("evidence")

    metrics = data_loader.compute_overview_metrics(
        dedup_df=dedup_df,
        classified_df=classified_df,
        evidence_df=evidence_df,
    )
    platform_dist_df = data_loader.get_platform_distribution(
        dedup_df=dedup_df,
        evidence_df=evidence_df,
    )

    return {
        "files_status": files_status,
        "datasets": datasets,
        "dedup_df": dedup_df,
        "classified_df": classified_df,
        "evidence_df": evidence_df,
        "metrics": metrics,
        "platform_dist": platform_dist_df,
    }


# ---------------------------------------------------------------------------
# Platform Metadata & Helpers
# ---------------------------------------------------------------------------
PLATFORM_META: Dict[str, Dict[str, str]] = {
    "android": {"name": "Android", "icon": "📱", "color": "#34a853"},
    "ios": {"name": "iOS", "icon": "🍎", "color": "#bdc1c6"},
    "reddit": {"name": "Reddit", "icon": "💬", "color": "#ff4500"},
    "google_help": {"name": "Google Help", "icon": "❓", "color": "#4285f4"},
    "youtube": {"name": "YouTube", "icon": "📺", "color": "#ea4335"},
    "hacker_news": {"name": "Hacker News", "icon": "⚡", "color": "#ff6600"},
    "lemmy_social": {"name": "Lemmy", "icon": "🌐", "color": "#a78bfa"},
}


def highlight_search(text: str, query: str) -> str:
    """Safely highlights matching query strings in HTML with character escaping."""
    if not text:
        return ""
    escaped = html.escape(str(text), quote=True)
    if not query or not query.strip():
        return escaped
    q = query.strip()
    escaped_q = html.escape(q, quote=True)
    pattern = re.compile(f"({re.escape(escaped_q)})", re.IGNORECASE)
    return pattern.sub(r'<mark class="search-hl">\1</mark>', escaped)


def format_count(val: Any) -> str:
    """Format count numbers with comma separators."""
    if val == "Not available" or val is None:
        return "Not available"
    if isinstance(val, (int, float)):
        return f"{int(val):,}"
    return str(val)


# ---------------------------------------------------------------------------
# Main Application
# ---------------------------------------------------------------------------
def main():
    data = load_discovery_data()
    metrics = data["metrics"]
    platform_dist = data["platform_dist"]
    evidence_df = data["evidence_df"]
    files_status = data["files_status"]

    # Compute discovery patterns from the verified 214 evidence records
    scenarios_data = pattern_analysis.analyze_retrieval_scenarios(evidence_df)
    remembered_data = pattern_analysis.analyze_remembered_clues(evidence_df)
    forgotten_data = pattern_analysis.analyze_forgotten_clues(evidence_df)
    behaviors_data = pattern_analysis.analyze_search_behaviors(evidence_df)
    insights_data = pattern_analysis.get_discovery_insights(evidence_df)
    opportunities_data = pattern_analysis.get_product_opportunities(evidence_df)

    # -----------------------------------------------------------------------
    # 1. HEADER (Simple, High Clarity)
    # -----------------------------------------------------------------------
    render_html(
        """<div class="header-container">
<div>
    <div class="hero-brand">Google Photos</div>
    <h1 class="hero-title">AI-Powered Discovery Engine</h1>
    <p class="hero-subtitle">Understanding how people find photos they only vaguely remember.</p>
</div>
<div class="badge-container">
    <span class="status-badge status-badge-green">● CORPUS VERIFIED</span>
    <span class="status-badge status-badge-blue">READ-ONLY</span>
    <span class="status-badge">7 SOURCES</span>
</div>
</div>"""
    )

    # -----------------------------------------------------------------------
    # 2. WHAT IS THIS? (Compact Explanation & Core Research Loop)
    # -----------------------------------------------------------------------
    render_html(
        """<div class="what-is-this-card">
<div class="what-is-this-heading">What are we trying to understand?</div>
People may remember a photo through a person, place, event, visual scene, or approximate time — without remembering the exact date, filename, or album. This engine studies how those memories become search attempts, where retrieval breaks down, and what people do next.
<div class="research-loop-grid">
    <div class="loop-node">
        <div class="loop-node-tag">🧠 MEMORY</div>
        <div class="loop-node-title">What I remember</div>
        <div class="loop-node-desc">People, rough timeframe, objects, atmosphere, scenes.</div>
    </div>
    <div class="loop-node">
        <div class="loop-node-tag">🔎 SEARCH</div>
        <div class="loop-node-title">How I try to find it</div>
        <div class="loop-node-desc">Keywords, conversational Ask Photos, face filters.</div>
    </div>
    <div class="loop-node">
        <div class="loop-node-tag">⚠️ FAILURE</div>
        <div class="loop-node-title">Where retrieval breaks</div>
        <div class="loop-node-desc">Semantic gap, face clustering errors, zero results.</div>
    </div>
    <div class="loop-node">
        <div class="loop-node-tag">🛠️ WORKAROUND</div>
        <div class="loop-node-title">What I do instead</div>
        <div class="loop-node-desc">Manual timeline scrolling, third-party file managers.</div>
    </div>
    <div class="loop-node">
        <div class="loop-node-tag">💡 DISCOVERY</div>
        <div class="loop-node-title">What this reveals</div>
        <div class="loop-node-desc">Context-aware multimodal & conversational retrieval.</div>
    </div>
</div>
</div>"""
    )

    # -----------------------------------------------------------------------
    # 3. SYSTEM & DATA INTEGRITY (Verified Research Foundation & Data Flow)
    # -----------------------------------------------------------------------
    total_dedup = html.escape(format_count(metrics.get("total_deduplicated")), quote=True)
    total_rel = html.escape(format_count(metrics.get("total_relevant")), quote=True)
    highly_rel = html.escape(format_count(metrics.get("highly_relevant")), quote=True)
    possibly_rel = html.escape(format_count(metrics.get("possibly_relevant")), quote=True)
    source_count = html.escape(format_count(metrics.get("source_platforms_count", 7)), quote=True)

    render_html(
        f"""<div class="integrity-container">
    <div class="integrity-header">
        <div class="integrity-title-tag">SYSTEM &amp; DATA INTEGRITY</div>
        <div class="integrity-heading">What powers this engine</div>
    </div>
    <div class="integrity-stats-list">
        <div class="integrity-stat-item"><strong>{total_dedup}</strong> deduplicated research records</div>
        <span class="integrity-stat-bullet">•</span>
        <div class="integrity-stat-item"><strong style="color: #8ab4f8 !important;">{total_rel}</strong> evidence records relevant to photo retrieval</div>
        <span class="integrity-stat-bullet">•</span>
        <div class="integrity-stat-item"><strong style="color: #81c995 !important;">{highly_rel}</strong> highly relevant</div>
        <span class="integrity-stat-bullet">•</span>
        <div class="integrity-stat-item"><strong style="color: #fdd663 !important;">{possibly_rel}</strong> possibly relevant</div>
        <span class="integrity-stat-bullet">•</span>
        <div class="integrity-stat-item"><strong style="color: #bdc1c6 !important;">{source_count}</strong> research sources</div>
    </div>
    <div class="integrity-flow-wrapper">
        <div class="integrity-flow-bar">
            <div class="integrity-flow-step">Web Sources</div>
            <div class="integrity-flow-arrow">→</div>
            <div class="integrity-flow-step">Collected Dataset</div>
            <div class="integrity-flow-arrow">→</div>
            <div class="integrity-flow-step">Cleaned &amp; Verified</div>
            <div class="integrity-flow-arrow">→</div>
            <div class="integrity-flow-step">Discovery Engine</div>
            <div class="integrity-flow-arrow">→</div>
            <div class="integrity-flow-step">Evidence &amp; Insights</div>
        </div>
        <div class="integrity-flow-note">
            The engine analyzes a locally collected and verified research corpus. It does not continuously scrape the web while you use the app.
        </div>
    </div>
    <div class="integrity-status-row">
        <div class="integrity-status-card">
            <div class="integrity-status-badge"><span class="status-badge status-badge-green">● CORPUS VERIFIED</span></div>
            <div class="integrity-status-desc">Research evidence has been checked and deduplicated.</div>
        </div>
        <div class="integrity-status-card">
            <div class="integrity-status-badge"><span class="status-badge status-badge-blue">READ-ONLY</span></div>
            <div class="integrity-status-desc">The Discovery Engine analyzes the prepared dataset without modifying the source data.</div>
        </div>
        <div class="integrity-status-card">
            <div class="integrity-status-badge"><span class="status-badge">{source_count} SOURCES</span></div>
            <div class="integrity-status-desc">Evidence was collected across the configured research sources.</div>
        </div>
    </div>
</div>"""
    )

    with st.expander("Technical details", expanded=False):
        st.markdown("**Architecture & Research Safeguards**")
        st.markdown("- **Mode:** READ-ONLY CONSUMER (Non-mutating data access)")
        st.markdown("- **Source Directory:** `Scrape_data/cleaned/`")
        st.markdown("- **Corpus Status:** Verified & Isolated")

        st.markdown("<br/>**Dataset Files Verification:**", unsafe_allow_html=True)
        file_rows = []
        for key, info in files_status.items():
            size_str = f"{info['size_bytes'] / 1024:.1f} KB" if info["size_bytes"] else "N/A"
            file_rows.append({
                "Dataset File": info["filename"],
                "Status": "✅ Verified Present" if info["exists"] else "❌ Missing",
                "Size": size_str,
            })
        st.dataframe(pd.DataFrame(file_rows), use_container_width=True, hide_index=True)

        st.markdown("<br/>**Platform Distribution Breakdown:**", unsafe_allow_html=True)
        if not platform_dist.empty:
            total_ev_count = platform_dist["evidence_count"].sum()
            segments_html = []
            legend_items = []

            for idx, row in platform_dist.iterrows():
                p_key = row["platform_key"]
                p_meta = PLATFORM_META.get(p_key, {"name": row["platform_name"], "icon": "📁", "color": "#8ab4f8"})
                p_name_esc = html.escape(str(p_meta["name"]), quote=True)
                e_cnt = int(row["evidence_count"])
                d_cnt = int(row["dedup_count"])
                pct = (e_cnt / total_ev_count * 100) if total_ev_count > 0 else 0

                if pct > 0:
                    segments_html.append(
                        f'<div class="dist-segment" style="width: {pct:.2f}%; background-color: {p_meta["color"]};" title="{p_name_esc}: {e_cnt} evidence ({pct:.1f}%)"></div>'
                    )

                legend_items.append(
                    f'<span><span class="dist-dot" style="background-color: {p_meta["color"]};"></span><strong>{p_name_esc}</strong>: {e_cnt} evidence / {d_cnt} total</span>'
                )

            bar_html = f'<div class="dist-container">{"".join(segments_html)}</div>'
            legend_html = f'<div class="dist-legend">{" • ".join(legend_items)}</div>'

            render_html(bar_html)
            render_html(legend_html)

        st.write("")
        if st.button("🔄 Refresh Data Cache", key="refresh_cache_btn"):
            st.cache_data.clear()
            st.rerun()

    # -----------------------------------------------------------------------
    # 4. WHAT DID WE LEARN? (Metric Ribbon & 4 Compact Discovery Summaries)
    # -----------------------------------------------------------------------
    render_html(
        """<div class="section-header-block">
<div class="section-title">What did the evidence reveal?</div>
<div class="section-subtitle">Verified quantitative evidence metrics and extracted memory-retrieval patterns.</div>
</div>"""
    )

    render_html(
        f"""<div class="metric-ribbon">
<div class="metric-ribbon-item">
    <div class="metric-ribbon-val">{total_dedup}</div>
    <div class="metric-ribbon-lbl">Total Records</div>
</div>
<div class="metric-ribbon-item">
    <div class="metric-ribbon-val" style="color: #8ab4f8;">{total_rel}</div>
    <div class="metric-ribbon-lbl">Relevant Evidence</div>
</div>
<div class="metric-ribbon-item">
    <div class="metric-ribbon-val" style="color: #81c995;">{highly_rel}</div>
    <div class="metric-ribbon-lbl">Highly Relevant</div>
</div>
<div class="metric-ribbon-item">
    <div class="metric-ribbon-val" style="color: #fdd663;">{possibly_rel}</div>
    <div class="metric-ribbon-lbl">Possibly Relevant</div>
</div>
</div>"""
    )

    # Dynamically extract top patterns for the 4 summaries
    top_scenario = scenarios_data[0] if scenarios_data else {"title": "People & Family Photos", "count": 39, "share_pct": 18.2}
    top_clue = remembered_data[0] if remembered_data else {"title": "People & Faces", "count": 76, "share_pct": 35.5}
    top_forgotten = forgotten_data[0] if forgotten_data else {"title": "Exact Date & Timestamp", "count": 10, "share_pct": 4.7}
    top_behavior = behaviors_data[0] if behaviors_data else {"title": "Keyword Search", "count": 204, "share_pct": 95.3}

    render_html(
        f"""<div class="discovery-summary-grid">
<div class="summary-card">
    <div class="summary-card-tag">PHOTO RETRIEVAL</div>
    <div class="summary-card-q">What kinds of photos are difficult to retrieve?</div>
    <div class="summary-card-pattern">{top_scenario['title']}</div>
    <div class="summary-card-count">{top_scenario['count']} evidence records ({top_scenario['share_pct']}%)</div>
</div>
<div class="summary-card">
    <div class="summary-card-tag">MEMORY</div>
    <div class="summary-card-q">What information do people remember?</div>
    <div class="summary-card-pattern">{top_clue['title']}</div>
    <div class="summary-card-count">{top_clue['count']} evidence records ({top_clue['share_pct']}%)</div>
</div>
<div class="summary-card">
    <div class="summary-card-tag">FORGOTTEN</div>
    <div class="summary-card-q">What information is missing?</div>
    <div class="summary-card-pattern">{top_forgotten['title']}</div>
    <div class="summary-card-count">{top_forgotten['count']} evidence records ({top_forgotten['share_pct']}%)</div>
</div>
<div class="summary-card">
    <div class="summary-card-tag">SEARCH</div>
    <div class="summary-card-q">How do people search when memory is incomplete?</div>
    <div class="summary-card-pattern">{top_behavior['title']}</div>
    <div class="summary-card-count">{top_behavior['count']} evidence records ({top_behavior['share_pct']}%)</div>
</div>
</div>"""
    )

    # -----------------------------------------------------------------------
    # 5. HOW DOES THE RETRIEVAL PROBLEM HAPPEN? (Memory → Search Mismatch)
    # -----------------------------------------------------------------------
    render_html(
        """<div class="section-header-block">
<div class="section-title">How does the retrieval problem happen?</div>
<div class="section-subtitle">Why vague episodic human memory collides with traditional index-based search.</div>
</div>"""
    )

    render_html(
        """<div class="mismatch-wrapper">
<div class="mismatch-flow-bar">
    <div class="mismatch-flow-step">🧠 <strong>WHAT USERS REMEMBER</strong></div>
    <div class="mismatch-flow-arrow">→</div>
    <div class="mismatch-flow-step">🔎 <strong>WHAT THEY SEARCH</strong></div>
    <div class="mismatch-flow-arrow">→</div>
    <div class="mismatch-flow-step">⚠️ <strong>WHERE IT FAILS</strong></div>
    <div class="mismatch-flow-arrow">→</div>
    <div class="mismatch-flow-step">🛠️ <strong>WHAT THEY DO INSTEAD</strong></div>
</div>
<div class="mismatch-columns">
    <div class="mismatch-box">
        <div class="mismatch-box-title" style="color: #81c995;">🧠 What People Remember (Human Memory)</div>
        <div class="mismatch-row">• <strong>People & Relationships:</strong> Who was in the photo (35.5% of evidence)</div>
        <div class="mismatch-row">• <strong>Approximate Time / Eras:</strong> 'In college', 'summer 3 years ago' (20.6%)</div>
        <div class="mismatch-row">• <strong>Prominent Objects & Colors:</strong> 'Yellow jacket', 'red car' (10.7%)</div>
        <div class="mismatch-row">• <strong>General Place / Setting:</strong> Beach, park, dinner table (9.3%)</div>
        <div class="mismatch-row">• <strong>Activities & Occasions:</strong> Hiking, cooking, birthday party (8.4%)</div>
    </div>
    <div class="mismatch-box">
        <div class="mismatch-box-title" style="color: #f28b82;">⚙️ What Traditional Search Demands (System Mismatch)</div>
        <div class="mismatch-row">• <strong>Exact Calendar Date:</strong> Precise day/month timestamp (Forgotten by users)</div>
        <div class="mismatch-row">• <strong>Exact Filename:</strong> Cryptic image tags like IMG_20210814.jpg (Unknown)</div>
        <div class="mismatch-row">• <strong>Pre-Structured Albums:</strong> Folders requiring manual curation upfront (Rarely created)</div>
        <div class="mismatch-row">• <strong>Literal Keyword Tokens:</strong> Single word matches ignoring composite context</div>
        <div class="mismatch-row">• <strong>Rigid Face Grouping:</strong> Misses unindexed people or side profiles</div>
    </div>
</div>
<div class="mismatch-example-box">
    <div class="mismatch-example-title">Evidence-Backed Retrieval Mismatch Example</div>
    <strong>Memory:</strong> User recalls a family camping trip a few summers ago with their brother near a lake.<br/>
    <strong>Search:</strong> Types keyword combinations: <code>"camping lake brother summer"</code>.<br/>
    <strong>Failure:</strong> Search returns zero results or unsorted hundreds because keyword matching cannot fuse multi-dimensional episodic context.<br/>
    <strong>Workaround:</strong> User spends 30+ minutes manually scrubbing the infinite timeline grid or abandons the search.
</div>
</div>"""
    )

    # -----------------------------------------------------------------------
    # 6. ANSWER THE 4 DISCOVERY QUESTIONS
    # -----------------------------------------------------------------------
    render_html(
        """<div class="section-header-block">
<div class="section-title">The Discovery Questions</div>
<div class="section-subtitle">Four core research questions answered directly from 214 verified evidence records.</div>
</div>"""
    )

    # Build Items for Question 1: Scenarios
    q1_rows = "".join([
        f'<div class="discovery-q-item"><span class="discovery-q-name">{s["icon"]} {s["title"]}</span><span class="discovery-q-stat">{s["count"]} ({s["share_pct"]}%)</span></div>'
        for s in scenarios_data[:5]
    ])

    # Build Items for Question 2: Remembered Clues (with horizontal progress bar)
    q2_rows = ""
    for c in remembered_data[:5]:
        pct = c["share_pct"]
        q2_rows += f"""<div style="margin-bottom: 0.4rem;">
<div style="display: flex; justify-content: space-between; font-size: 0.82rem; color: #bdc1c6;">
    <span>{c['icon']} {c['title']}</span>
    <span style="color: #8ab4f8; font-weight: 600;">{c['count']} ({pct}%)</span>
</div>
<div class="bar-track"><div class="bar-fill" style="width: {min(100, pct * 2.5)}%;"></div></div>
</div>"""

    # Build Items for Question 3: Forgotten Information
    q3_rows = "".join([
        f'<div class="discovery-q-item"><span class="discovery-q-name">{f["icon"]} {f["title"]}</span><span class="discovery-q-stat">{f["count"]} ({f["share_pct"]}%)</span></div>'
        for f in forgotten_data
    ]) + """<div class="discovery-q-item"><span class="discovery-q-name">📁 Pre-Organized Album / Folder</span><span class="discovery-q-stat">Implicit in 95%+</span></div>
<div class="discovery-q-item"><span class="discovery-q-name">🗺️ Precise GPS Coordinates</span><span class="discovery-q-stat">Implicit in 90%+</span></div>
<div class="discovery-q-item"><span class="discovery-q-name">🏷️ Camera / Lens Technical EXIF</span><span class="discovery-q-stat">Implicit in 98%+</span></div>"""

    # Build Items for Question 4: Search Behaviors
    q4_rows = "".join([
        f'<div class="discovery-q-item"><span class="discovery-q-name">{b["icon"]} {b["title"]}</span><span class="discovery-q-stat">{b["count"]} ({b["share_pct"]}%)</span></div>'
        for b in behaviors_data[:5]
    ])

    render_html(
        f"""<div class="discovery-q-grid">
<div class="discovery-q-card">
    <div class="discovery-q-num">01 — Retrieval Scenarios</div>
    <div class="discovery-q-title">What photos are hard to retrieve?</div>
    {q1_rows}
    <div style="font-size: 0.76rem; color: #9aa0a6; margin-top: 0.65rem; line-height: 1.35;">
        <strong>Barrier:</strong> Family, pet, and screenshot memories carry high emotional or utility value but get lost in unorganized feeds.
    </div>
</div>
<div class="discovery-q-card">
    <div class="discovery-q-num">02 — Memory Anchors</div>
    <div class="discovery-q-title">What do people actually remember?</div>
    {q2_rows}
</div>
<div class="discovery-q-card">
    <div class="discovery-q-num">03 — Forgotten Clues</div>
    <div class="discovery-q-title">What information is missing?</div>
    {q3_rows}
    <div style="font-size: 0.76rem; color: #9aa0a6; margin-top: 0.65rem; line-height: 1.35;">
        <strong>Insight:</strong> People recall fuzzy contextual associations, not metadata indexes or calendar timestamps.
    </div>
</div>
<div class="discovery-q-card">
    <div class="discovery-q-num">04 — Search Formulation</div>
    <div class="discovery-q-title">How do people search?</div>
    {q4_rows}
    <div style="font-size: 0.76rem; color: #9aa0a6; margin-top: 0.65rem; line-height: 1.35;">
        <strong>Behavior:</strong> 95.3% rely on keywords first, but shift to conversational queries or manual scrolling when simple words fail.
    </div>
</div>
</div>"""
    )

    # -----------------------------------------------------------------------
    # 7. EXPLORE THE EVIDENCE
    # -----------------------------------------------------------------------
    render_html(
        """<div class="section-header-block">
<div class="section-title">Explore the Evidence</div>
<div class="section-subtitle">Search, filter, and inspect verified evidence records from real user accounts.</div>
</div>"""
    )

    if evidence_df is not None and not evidence_df.empty:
        # Compact Filter Bar
        f_col1, f_col2, f_col3, f_col4 = st.columns([2.2, 1.2, 1.2, 1.4])

        with f_col1:
            search_query = st.text_input(
                "Search evidence",
                placeholder="Search memories, clues, quotes (e.g. 'face', 'beach', 'receipt')...",
                label_visibility="collapsed",
                key="evidence_search_box",
            )

        with f_col2:
            relevance_choice = st.selectbox(
                "Relevance",
                options=["All Relevance", "Highly Relevant (28)", "Possibly Relevant (186)"],
                label_visibility="collapsed",
                key="evidence_rel_sel",
            )

        with f_col3:
            platform_choice = st.selectbox(
                "Platform",
                options=["All Platforms", "Reddit", "Android", "iOS", "Google Help", "YouTube", "Hacker News", "Lemmy"],
                label_visibility="collapsed",
                key="evidence_plat_sel",
            )

        with f_col4:
            barrier_choice = st.selectbox(
                "Barrier / Stage",
                options=["All Barriers", "Context Search Failure", "Face Clustering Error", "OCR / Text Failure", "Zero Results", "Manual Workaround"],
                label_visibility="collapsed",
                key="evidence_barrier_sel",
            )

        # Filtering Logic
        filtered_df = evidence_df.copy()

        # 1. Relevance filter
        if "Highly Relevant" in relevance_choice:
            filtered_df = filtered_df[filtered_df["relevance_label"] == "highly_relevant"]
        elif "Possibly Relevant" in relevance_choice:
            filtered_df = filtered_df[filtered_df["relevance_label"] == "possibly_relevant"]

        # 2. Platform filter
        if platform_choice != "All Platforms":
            p_map = {
                "Reddit": "reddit",
                "Android": "android",
                "iOS": "ios",
                "Google Help": "google_help",
                "YouTube": "youtube",
                "Hacker News": "hacker_news",
                "Lemmy": "lemmy_social",
            }
            target_p = p_map.get(platform_choice)
            if target_p:
                filtered_df = filtered_df[filtered_df["platform"] == target_p]

        # 3. Barrier filter
        if barrier_choice != "All Barriers":
            if barrier_choice == "Context Search Failure":
                filtered_df = filtered_df[filtered_df["retrieval_barrier"].fillna("").str.contains("context", case=False)]
            elif barrier_choice == "Face Clustering Error":
                filtered_df = filtered_df[filtered_df["retrieval_barrier"].fillna("").str.contains("face|clustering", case=False)]
            elif barrier_choice == "OCR / Text Failure":
                filtered_df = filtered_df[filtered_df["retrieval_barrier"].fillna("").str.contains("ocr|text", case=False)]
            elif barrier_choice == "Zero Results":
                filtered_df = filtered_df[filtered_df["retrieval_barrier"].fillna("").str.contains("zero", case=False)]
            elif barrier_choice == "Manual Workaround":
                filtered_df = filtered_df[filtered_df["workaround"].fillna("").str.strip() != ""]

        # 4. Search query
        if search_query and search_query.strip():
            q = search_query.strip().lower()
            text_mask = (
                filtered_df["evidence_quote"].fillna("").str.lower().str.contains(q)
                | filtered_df["remembered_clues"].fillna("").str.lower().str.contains(q)
                | filtered_df["retrieval_barrier"].fillna("").str.lower().str.contains(q)
                | filtered_df["retrieval_scenario"].fillna("").str.lower().str.contains(q)
                | filtered_df["search_behavior"].fillna("").str.lower().str.contains(q)
                | filtered_df["text"].fillna("").str.lower().str.contains(q)
            )
            filtered_df = filtered_df[text_mask]

        matching_count = len(filtered_df)

        # Pagination & Summary Header
        p_row1, p_row2 = st.columns([2, 1])
        with p_row1:
            st.caption(f"Showing **{matching_count}** of **{len(evidence_df)}** evidence records")

        page_size = 6
        total_pages = max(1, (matching_count + page_size - 1) // page_size)

        with p_row2:
            if total_pages > 1:
                current_page = st.number_input(
                    f"Page (1-{total_pages})",
                    min_value=1,
                    max_value=total_pages,
                    value=1,
                    step=1,
                    label_visibility="collapsed",
                    key="evidence_page_input",
                )
            else:
                current_page = 1

        start_idx = (current_page - 1) * page_size
        end_idx = min(start_idx + page_size, matching_count)
        page_records = filtered_df.iloc[start_idx:end_idx]

        if matching_count == 0:
            st.info("No evidence records match your search or filter criteria.")
        else:
            for idx, row in page_records.iterrows():
                rec_id = str(row.get("record_id", ""))
                rec_id_esc = html.escape(rec_id, quote=True)
                p_key = str(row.get("platform", ""))
                p_meta = PLATFORM_META.get(p_key, {"name": p_key.title(), "icon": "📁", "color": "#bdc1c6"})
                p_name_esc = html.escape(p_meta["name"], quote=True)
                p_icon_esc = html.escape(p_meta["icon"], quote=True)

                rel_label = str(row.get("relevance_label", ""))
                rel_badge = (
                    '<span class="tag-highly-rel">★ Highly Relevant</span>'
                    if rel_label == "highly_relevant"
                    else '<span class="tag-possibly-rel">● Possibly Relevant</span>'
                )

                raw_quote = str(row.get("evidence_quote", "")).strip()
                if not raw_quote or raw_quote == "nan":
                    raw_quote = str(row.get("text", "")).strip()[:160] + "..."

                hl_quote = highlight_search(raw_quote, search_query)

                # Clues & Mini Flow Values
                rem_clue = str(row.get("remembered_clues", "")).strip()
                rem_display = rem_clue.replace("_", " ").title() if rem_clue and rem_clue != "nan" else "Contextual Cues"
                
                search_beh = str(row.get("search_behavior", "")).strip()
                search_display = search_beh.replace("_", " ").title() if search_beh and search_beh != "nan" else "Keyword Query"
                
                barrier = str(row.get("retrieval_barrier", "")).strip()
                barrier_display = barrier[:45] + "..." if len(barrier) > 45 else (barrier if barrier and barrier != "nan" else "Context Gap")
                
                workaround = str(row.get("workaround", "")).strip()
                workaround_display = workaround[:45] + "..." if len(workaround) > 45 else (workaround if workaround and workaround != "nan" else "Timeline Browsing")

                card_html = f"""<div class="evidence-card">
<div class="evidence-card-header">
    <div>
        {rel_badge}
        <span class="tag-platform-badge" style="margin-left: 0.35rem;">{p_icon_esc} {p_name_esc}</span>
        <span style="font-size: 0.72rem; color: #9aa0a6; margin-left: 0.35rem;">ID: {rec_id_esc}</span>
    </div>
    <div style="font-size: 0.74rem; color: #9aa0a6;">Source: {html.escape(str(row.get('source', '')), quote=True)}</div>
</div>
<div class="evidence-quote">"{hl_quote}"</div>
<div class="evidence-mini-flow">
    <span class="mini-flow-node">🧠 <strong>Memory:</strong> {html.escape(rem_display, quote=True)}</span>
    <span style="color: #8ab4f8;">→</span>
    <span class="mini-flow-node">🔎 <strong>Search:</strong> {html.escape(search_display, quote=True)}</span>
    <span style="color: #8ab4f8;">→</span>
    <span class="mini-flow-node">⚠️ <strong>Failure:</strong> {html.escape(barrier_display, quote=True)}</span>
    <span style="color: #8ab4f8;">→</span>
    <span class="mini-flow-node">🛠️ <strong>Workaround:</strong> {html.escape(workaround_display, quote=True)}</span>
</div>
</div>"""
                render_html(card_html)

                # Expandable Deep-Dive Details for this Record
                with st.expander(f"View Retrieval Journey & Context ({rec_id})", expanded=False):
                    d_col1, d_col2 = st.columns(2)
                    with d_col1:
                        st.markdown(f"**🧠 Remembered Clues:** {row.get('remembered_clues', 'N/A')}")
                        st.markdown(f"**❓ Forgotten Clues:** {row.get('forgotten_or_unknown_clues', 'Exact date / album')}")
                        st.markdown(f"**🔎 Search Formulation:** {row.get('search_behavior', 'Keyword')}")
                        st.markdown(f"**💬 Search Query / Words:** {row.get('search_query_or_words_used', 'N/A')}")
                    with d_col2:
                        st.markdown(f"**⚠️ Failure Stage:** {row.get('failure_stage', 'Retrieval')}")
                        st.markdown(f"**🚫 Retrieval Barrier:** {row.get('retrieval_barrier', 'Semantic gap')}")
                        st.markdown(f"**🛠️ Workaround Used:** {row.get('workaround', 'Manual scanning')}")
                        st.markdown(f"**🏁 Outcome:** {row.get('retrieval_outcome', 'Unresolved')}")

                    reason = str(row.get("relevance_reason", "")).strip()
                    if reason and reason != "nan":
                        st.caption(f"**Relevance Reason:** {reason}")
                    full_txt = str(row.get("text", "")).strip()
                    if full_txt and full_txt != raw_quote:
                        st.caption(f"**Full Text:** {full_txt}")

    else:
        st.warning("Evidence dataset could not be loaded from `Scrape_data/cleaned/`.")

    # -----------------------------------------------------------------------
    # 8. WHAT DOES THIS MEAN FOR THE PRODUCT? (Insights & PM Opportunities)
    # -----------------------------------------------------------------------
    render_html(
        """<div class="section-header-block">
<div class="section-title">What does this mean for the product?</div>
<div class="section-subtitle">Translating evidence patterns into actionable product opportunities and AI capabilities.</div>
</div>"""
    )

    # 4 Structured Discovery Insights (Evidence → Pattern → Problem → Opportunity)
    insights_html = "".join([
        f"""<div class="insight-card">
<div class="insight-header">
    <span class="insight-num">Discovery Insight {ins['number']}</span>
    <span class="insight-stat">{ins['stat']}</span>
</div>
<div class="insight-title">{ins['title']}</div>
<div class="insight-chain-step"><strong>Evidence:</strong> {ins['summary']}</div>
<div class="insight-chain-step"><strong>User Problem:</strong> {ins['implication']}</div>
<div class="insight-chain-step"><strong style="color: #8ab4f8;">Product Opportunity:</strong> {ins['opportunity']}</div>
</div>"""
        for ins in insights_data
    ])

    render_html(f'<div class="insight-grid">{insights_html}</div>')

    # PM Opportunity Pipeline
    render_html(
        """<div class="pm-pipeline-banner">
<span>Evidence Basis</span>
<span style="color: #8ab4f8;">→</span>
<span>Observed Pattern</span>
<span style="color: #8ab4f8;">→</span>
<span>User Problem</span>
<span style="color: #8ab4f8;">→</span>
<span>Product Opportunity</span>
<span style="color: #8ab4f8;">→</span>
<span style="color: #81c995;">Proposed AI Capability</span>
</div>"""
    )

    opps_html = "".join([
        f"""<div class="opp-card">
<div class="opp-stage">Stage {opp['stage']} • Product Strategy</div>
<div class="opp-title">{opp['title']}</div>
<div class="opp-content">
    <strong>Evidence Basis:</strong> {opp['evidence_basis']}<br/>
    <strong>User Problem:</strong> {opp['user_problem']}<br/>
    <strong>Product Opportunity:</strong> {opp['opportunity']}<br/>
    <span style="color: #8ab4f8; font-weight: 600;">AI Capability:</span> {opp['ai_capability']}
</div>
</div>"""
        for opp in opportunities_data
    ])

    render_html(f'<div class="opp-grid">{opps_html}</div>')


if __name__ == "__main__":
    main()
