# Google Photos Discovery Engine — Data Collection Layer

A structured, evidence-preserving data collection layer for PM research on **AI-Powered Discovery Engine for Vaguely Remembered Photo Retrieval**.

This pipeline collects, normalizes, deduplicates, and exports publicly available user discussions and reviews regarding Google Photos search behavior, vague description queries, timeline scrolling workarounds, and search regression reports.

---

## 📁 Directory Structure

```text
GooglePhotos_Discovery_Engine/
├── collectors/
│   ├── google_play.py              # Google Play Store reviews collector (com.google.android.apps.photos)
│   ├── app_store.py                # Apple App Store reviews collector (iOS ID: 962194608)
│   ├── reddit.py                   # Reddit post/discussion collector (r/googlephotos, etc.)
│   ├── google_photos_community.py  # Google Help Community thread collector
│   ├── youtube.py                  # YouTube comments collector (YouTube Data API v3)
│   ├── forums.py                   # Public forums collector (Hacker News Algolia API)
│   └── social_media.py             # Public social media collector (Bluesky & Mastodon)
├── scrape_data/
│   ├── raw/
│   │   ├── google_play/            # Source-specific raw CSV files
│   │   ├── app_store/
│   │   ├── reddit/
│   │   ├── google_photos_community/
│   │   ├── youtube/
│   │   ├── forums/
│   │   ├── social_media/
│   │   ├── all_sources_raw.csv     # Master aggregated raw corpus
│   │   └── archive/                # Historical collection run archives
│   ├── cleaned/
│   │   └── all_sources_deduplicated.csv # Multi-tier deduplicated corpus
│   ├── collection_log.csv          # Execution audit log
│   └── collection_summary.csv      # Data completeness & quality metrics
├── utils/
│   ├── normalization.py            # 12-column canonical schema enforcement & ISO timestamping
│   ├── deduplication.py            # Multi-tier deduplication engine
│   └── logging_utils.py            # Quality metrics, logging, and archival routines
├── config/
│   └── search_queries.yaml         # Configurable search queries & retrieval keywords
├── collect_all.py                  # Master orchestration CLI
├── requirements.txt                # Python dependencies
├── .env.example                    # API credentials template
├── .gitignore
└── README.md
```

---

## 📊 Normalized Record Schema

Every collected record is standardized to the following 12-column schema:

| Column | Type | Description |
| :--- | :--- | :--- |
| `record_id` | String | Unique, deterministic identifier (`<source>_<id>` or `<source>_<hash>`) |
| `source` | String | Data source name (`google_play`, `app_store`, `reddit`, etc.) |
| `platform` | String | Platform (`android`, `ios`, `reddit`, `google_help`, `bluesky`, etc.) |
| `source_id` | String | Native platform ID for the review/post/thread |
| `url` | String | Direct canonical URL to the post or thread |
| `title` | String | Title of post, thread, or review (empty if unavailable) |
| `author` | String | Author username or display name |
| `text` | String | **Original raw user text preserved verbatim** |
| `published_at` | String | ISO 8601 formatted publication timestamp |
| `rating` | String/Number | Numerical rating/score (e.g. 1-5 for app stores, score for reddit/HN) |
| `language` | String | Language code (default `en`) |
| `search_query` | String | Search term/keyword that yielded this record |
| `collected_at` | String | ISO 8601 timestamp of collection run |

---

## 🚀 How to Run

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Credentials (Optional)
If you have authorized developer keys (e.g., for YouTube comments or Reddit PRAW), copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
*Note: If API credentials are not configured, collectors gracefully use public search endpoints or log status without failing.*

### 3. Run Test Collection (~20–40 records per source)
```bash
python collect_all.py --test
```

### 4. Run Full-Scale Collection
```bash
python collect_all.py --full
```

### 5. Run a Specific Source Only
```bash
python collect_all.py --source google_play --limit 50
python collect_all.py --source reddit --limit 50
```

---

## 🛡️ Research Integrity & Preservation
- **No Text Alteration**: Original user wording, spelling, and tone are strictly preserved.
- **No Synthetic Records**: Only genuine records retrieved from public endpoints are stored.
- **Deduplication Without Data Loss**: Raw evidence is preserved in `scrape_data/raw/`, while deduplicated results are written separately to `scrape_data/cleaned/all_sources_deduplicated.csv`.
- **No Premature AI Processing**: Embeddings, sentiment classification, and clustering are deferred to Phase 2.
