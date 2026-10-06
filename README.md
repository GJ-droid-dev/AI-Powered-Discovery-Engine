# Google Photos — AI-Powered Memory Retrieval Discovery Engine

> **Diagnosing how human episodic memory fails when interacting with Google Photos search, deconstructing cognitive memory models, and prioritizing high-impact AI retrieval opportunities.**

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![LLM](https://img.shields.io/badge/LLM-Gemini_3.8_Flash-orange.svg)](https://deepmind.google/technologies/gemini/)
[![Embeddings](https://img.shields.io/badge/Embeddings-BGE_Small_v1.5-brightgreen.svg)](https://huggingface.co/BAAI/bge-small-en-v1.5)
[![Framework](https://img.shields.io/badge/Dashboard-Streamlit_1.30-red.svg)](https://streamlit.io/)
[![Tests](https://img.shields.io/badge/Tests-45_Passing-success.svg)](https://pytest.org/)

---

## 🌐 Live Interactive Testing Link

The workflow can be tested live in an interactive Streamlit dashboard:

- **Local Access**: [http://localhost:8501](http://localhost:8501)
- **Public Tunnel Access**: [https://two-places-behave.loca.lt](https://two-places-behave.loca.lt)  
  *(If prompted for tunnel password, enter host endpoint IP: `38.254.176.6`)*

### Testing the Workflow Live
On the Home Page, scroll to **"🧪 Test the Discovery Engine Workflow Live"**:
1. Select a pre-loaded test scenario (e.g. *Case 1: Conjunctive Failure (Person + Event)* or *Case 2: Visual Detail*) or enter your own custom query complaint.
2. Click **"🚀 Run Live AI Diagnosis"**.
3. Watch the engine classify relevance, assign a taxonomy category, deconstruct the user's cognitive memory model (remembered cues vs. forgotten metadata), compute severity, and formulate a product diagnosis in real-time.

---

## 📌 Problem Context & Product Motivation

Human episodic memory is associative, sensory, and narrative:
- *"My yellow suitcase in the hotel room"*
- *"Dave and Sarah dancing at our wedding"*
- *"Candid genuine laughter on the beach with friends"*

In contrast, traditional photo search engines rely on **rigid metadata** (exact calendar dates, GPS coordinates, camera filenames) or **isolated object detection** (identifying a single dog or car without relational context).

This project audits **558 real user feedback records** collected from **4 public channels** (Google Play Store, Apple App Store, Reddit r/googlephotos, Google Support Community) to discover where search fails, categorize the breakdowns into a grounded taxonomy, extract cognitive memory cues, and prioritize the top product opportunity areas.

---

## 🏗️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                      DATA COLLECTION LAYER                             │
│  Reddit (PRAW)  │  Play Store Scraper  │ App Store RSS │ Support Forum │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ 558 Raw Records
┌────────────────────────────────────▼───────────────────────────────────┐
│                    NORMALIZATION & DEDUPLICATION                       │
│      PII Redaction (Regex + spaCy)  │  SHA-256 Content Deduplication    │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │ 558 Clean Records
┌────────────────────────────────────▼───────────────────────────────────┐
│                         ANALYSIS ENGINE                                │
│  Stage 2A: Relevance Filter (2-Pass: 21 Regex Patterns + Gemini 3.8)   │
│            → 98 Genuine Retrieval Failures (17.6% capture rate)        │
│  Stage 2B: Failure Categorizer (Gemini Flash + BGE DBSCAN Clustering)  │
│            → 8 Grounded Categories + 1 Emergent Discovery Cluster      │
│  Stage 2C: Cognitive Memory Model Extractor                            │
│            → Deconstructs Remembered vs. Forgotten Attributes          │
│  Stage 2D: Aggregation & Severity Scoring                              │
│            → Composite Severity: 0.4*Lang + 0.3*Star + 0.3*Churn       │
│            → Opportunity Ranking: 0.4*Vol + 0.4*Sev + 0.2*Feasibility  │
└────────────────────────────────────┬───────────────────────────────────┘
                                     │
┌────────────────────────────────────▼───────────────────────────────────┐
│                     OUTPUTS & CONSUMPTION LAYER                        │
│  • Executive Report: data/outputs/discovery_report.md                  │
│  • Searchable Evidence Library: data/outputs/evidence_library.csv/json │
│  • Interactive Multi-Page Streamlit Dashboard (dashboard/app.py)       │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Key Findings & Grounded Taxonomy

### 1. The Cognitive Recall Gap
- **What Users Remember**:
  - Visual Details (clothing, colors, distinctive props): **89.8%** of queries
  - Social Co-occurrence (specific friends/family together): **75.5%**
  - Event Context & Vibe (candid laughter, wedding dance): **65.3%**
  - Temporal Approximation (seasons, life phases): **58.2%**
- **What Users Forget**:
  - Exact Calendar Date: **77.6% forgotten**
  - Exact Location / GPS: **77.6% forgotten**
  - File Name / Format: **98.0% forgotten**

### 2. Opportunity Area Prioritization

| Rank | Failure Category | Complaints | % Share | Severity (0-100) | Opportunity Score | Strategic Priority |
|:----:|:-----------------|:----------:|:-------:|:----------------:|:-----------------:|:------------------:|
| **1** | **Emergent: Chronological & Date Overrides** | 43 | 43.9% | 32.2 | **66.9** | 🔴 Priority 1: Fix Now |
| **2** | **People + Event Co-occurrence** | 19 | 19.4% | 23.2 | **41.0** | 🔴 Priority 1: Fix Now |
| **3** | **Document & Screenshot OCR** | 15 | 15.3% | 16.0 | **37.3** | 🟡 Priority 2: High Feasibility |
| **4** | **Visual Detail / Color Binding** | 13 | 13.3% | 16.7 | **35.8** | 🔵 Priority 3: Friction Point |
| **5** | **Contextual & Episodic Context** | 13 | 13.3% | 24.0 | **34.7** | 🟡 Priority 2: Core Need |
| **6** | **Temporal Approximation** | 9 | 9.2% | 22.1 | **33.2** | 🔵 Priority 3: Natural Language |
| **7** | **Object in Scene** | 6 | 6.1% | 20.8 | **28.9** | ⚪ Priority 4: Incremental |
| **8** | **Emotional Association** | 4 | 4.1% | 20.6 | **24.0** | ⚪ Priority 4: Specialized |

---

## 🚀 Getting Started

### Prerequisites
- Python 3.11 or 3.12
- Node.js (optional, for localtunnel public sharing)
- Google Gemini API Key (`GEMINI_API_KEY`)

### Installation
```bash
# Clone the repository
git clone <repo-url>
cd google-photos-discovery-engine

# Create and activate virtual environment
python -m venv .venv
# On Windows:
.\.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Configure environment variables
cp .env.example .env
# Edit .env and set your GEMINI_API_KEY
```

---

## 💻 CLI Commands

The CLI provides modular and unified pipeline execution:

```bash
# 1. Run full end-to-end pipeline (Collect → Analyze → Report)
python main.py run

# 2. Collect raw feedback records from 4 public sources
python main.py collect

# 3. Execute analysis pipeline (Relevance, Categorization, Memory Extraction, Aggregation)
python main.py analyze

# 4. Generate the executive markdown report
python main.py report

# 5. Search the evidence library from terminal
python main.py evidence "wedding"
python main.py evidence "receipt" --category document_screenshot --limit 3

# 6. Launch the interactive Streamlit dashboard
streamlit run dashboard/app.py
```

---

## 🖥️ Streamlit Dashboard Walkthrough

The dashboard contains 5 dedicated interactive views:

1. **Executive Home (`app.py`)**: Top-level KPI cards, opportunity bar chart, source breakdown donut chart, and the **Live Workflow Test Runner**.
2. **Category Explorer (`01_category_explorer.py`)**: Deep dive into individual failure modes, cognitive memory profiles, and representative quotes with source links.
3. **Memory Heatmap (`02_memory_heatmap.py`)**: 2D matrix of Remembered vs. Forgotten cues and the Human vs. System Cognitive Gap chart.
4. **Opportunity Ranker (`03_opportunity_ranker.py`)**: 2x2 Quadrant scatter plot (Severity vs. Volume) with interactive weight tuning sliders and CSV export.
5. **Evidence Search (`04_evidence_search.py`)**: Full-text keyword search over all 98 analyzed complaints with severity indicators and source links.
6. **Report Viewer (`05_report_viewer.py`)**: Full executive report reader with one-click download buttons for Markdown, CSV, and JSON artifacts.

---

## 🧪 Testing & Validation

Run the comprehensive automated test suite:

```bash
pytest tests/ -v
```

All 45+ unit and integration tests validate:
- PII sanitization (emails, phone numbers, mentions, URLs)
- SHA-256 deduplication and caching
- Relevance filtering keyword logic and LLM boundaries
- Failure categorization taxonomy assignment
- BGE dense embedding DBSCAN clustering
- Cognitive memory model schema extraction
- Composite severity and opportunity ranking math
- Evidence library indexing and search
- Jinja2 report rendering
- Full pipeline integration flow

---

## 📄 License & Attribution
Designed and built for the NextLeap AI Product Management Discovery Project.
Data collected exclusively from public user feedback forums and app reviews under fair-use research guidelines.
All user identifiers and personal data redacted prior to analysis.
