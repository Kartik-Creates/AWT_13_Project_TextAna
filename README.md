<p align="center">
  <img src="frontend/public/favicon.svg" width="64" alt="Loops Logo" />
</p>

<h1 align="center">Loops — AI Content Moderation Engine</h1>

<p align="center">
  <strong>Production-grade AI moderation pipeline powering the Loops developer platform</strong><br/>
  Dual-approach content filtering · Real-time analytics · Human-in-the-loop review
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/FastAPI-0.104-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black" alt="React" />
  <img src="https://img.shields.io/badge/PyTorch-2.10-EE4C2C?style=flat-square&logo=pytorch&logoColor=white" alt="PyTorch" />
  <img src="https://img.shields.io/badge/MongoDB-7.0-47A248?style=flat-square&logo=mongodb&logoColor=white" alt="MongoDB" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-4.2-06B6D4?style=flat-square&logo=tailwindcss&logoColor=white" alt="Tailwind" />
</p>

---

## Why This System Is Critical for Loops

**Loops** is a developer-focused social platform that exclusively allows **technology-related content** — coding discussions, architecture debates, DevOps workflows, ML experiments, and open-source collaboration. Unlike general-purpose social networks, Loops has a **zero tolerance for off-topic noise**, and every post must survive a multi-layered AI gauntlet before it reaches the feed.

Without this moderation engine, the platform would face:

| Threat | Impact on Loops |
|--------|----------------|
| **Off-topic spam** (food, sports, politics, motivational quotes) | Dilutes the developer signal; users abandon the platform |
| **Toxic / hate speech** | Violates community trust; legal liability |
| **Disguised abuse** (leetspeak, Hindi/Hinglish slurs, Unicode tricks) | Bypasses naive keyword filters; poisons discussions |
| **Content sandwiching** (wrapping off-topic text between tech sentences) | Tricks simple classifiers; degrades feed quality |
| **NSFW / explicit images** | Immediate community violation; reputational damage |
| **Phishing / scam URLs** | Security risk to developer audience |

This moderation system is the **immune system of Loops** — it processes every single post through a sequential, multi-model AI pipeline, ensures only genuine tech content enters the feed, and routes borderline cases to human reviewers instead of making irreversible decisions.

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Dual Moderation Approaches](#dual-moderation-approaches)
- [ML Model Stack](#ml-model-stack)
- [Frontend Dashboard](#frontend-dashboard)
- [API Reference](#api-reference)
- [Project Structure](#project-structure)
- [Installation & Setup](#installation--setup)
- [Environment Variables](#environment-variables)
- [Resource Footprint](#resource-footprint)
- [Testing](#testing)
- [Contributors](#contributors)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LOOPS PLATFORM — POST FLOW                     │
│                                                                         │
│   User Post ──▶ Text Normalization ──▶ Rule Engine (Deterministic)      │
│                       │                       │                         │
│                       ▼                       ▼                         │
│            ┌─────────────────┐    ┌──────────────────────┐              │
│            │  APPROACH 1     │    │    APPROACH 2         │              │
│            │  Ensemble       │    │    Ollama LLM         │              │
│            │  (Multi-Model)  │    │    (Llama 3.2 3B)     │              │
│            └────────┬────────┘    └──────────┬───────────┘              │
│                     │                        │                          │
│                     ▼                        ▼                          │
│              Decision Engine ◄───────────────┘                          │
│                     │                                                   │
│            ┌────────┼────────┐                                          │
│            ▼        ▼        ▼                                          │
│         ALLOW    BLOCK    HUMAN REVIEW                                  │
│           │        │         │                                          │
│           ▼        ▼         ▼                                          │
│        ┌─Feed─┐  ┌─Rejected─┐  ┌─Moderation Queue─┐                   │
│        │      │  │  + reason │  │  Admin Dashboard  │                   │
│        └──────┘  └──────────┘  └──────────────────┘                    │
└─────────────────────────────────────────────────────────────────────────┘
```

The system follows a **sequential pipeline architecture** where content progresses through increasingly sophisticated layers:

1. **Text Normalization** — Strips leetspeak, Unicode obfuscation, disguised URLs, and Hindi/Hinglish evasion patterns
2. **Rule Engine** — Deterministic checks: keyword matching, regex for spam/scam/URLs, content mixing detection, Hindi abuse detection, tech relevance scoring
3. **ML Analysis** — Approach-specific deep learning models analyze toxicity, hate speech, intent, and tech relevance
4. **Image Analysis** — NSFW detection + CLIP-based tech-visual relevance scoring
5. **Decision Engine** — Aggregates all signals into a final verdict: `ALLOW`, `BLOCK`, or `HUMAN_REVIEW`
6. **Explanation Builder** — Translates internal rejection codes into human-readable explanations

---

## Dual Moderation Approaches

The system ships with **two independent moderation approaches**, switchable via the `MODERATION_APPROACH` environment variable. Both share the same Rule Engine and preprocessing pipeline but differ in how they determine tech relevance.

### Approach 1: Ensemble (Multi-Model) — `MODERATION_APPROACH=ensemble`

A stack of **six specialized ML models** working in sequence:

| Stage | Model | Role |
|-------|-------|------|
| Toxicity Detection | `unitary/toxic-bert` (BERT 110M) | Multi-label toxicity, threats, obscenity |
| Hate Speech | `Hate-speech-CNERG/dehatebert-mono-english` (BERT 110M) | Dedicated hate speech classification |
| Intent & Entity | spaCy `en_core_web_sm` (CNN Trigram) | NER + dependency parsing for cyber threat intents |
| Tech Context | `cross-encoder/nli-deberta-v3-base` (DeBERTa 86M) | Zero-shot NLI to distinguish tech tutorials from malicious guides |
| **Tech Relevance** | `all-MiniLM-L6-v2` (Sentence Transformers) | **Context-aware semantic similarity** — compares posts against tech/off-topic anchor embeddings |
| Visual Analysis | `openai/clip-vit-base-patch32` + `Falconsai/nsfw_image_detection` | CLIP tech-image relevance + ViT NSFW detection |

**Human Review Trigger:** Posts that pass the Rule Engine + toxicity/hate models but are rejected by **DeBERTa** for being non-tech/off-topic → flagged for human moderation instead of auto-blocking.

### Approach 2: Ollama LLM — `MODERATION_APPROACH=ollama`

A single **Llama 3.2 (3B)** model running locally via Ollama, acting as a **tech-relevance judge only**:

- All harm detection (drugs, abuse, spam, threats) is handled by the upstream Rule Engine
- Ollama only answers: *"Is this post genuinely about technology?"*
- Returns a structured JSON with `tech_relevance` (0.0–1.0), `zone` (tech/review/off_topic), and `reason`
- **Fallback hierarchy**: If Ollama is unavailable → Rule Engine keyword scoring → route to human review

**Human Review Trigger:** Posts that pass the Rule Engine (no harm) but are rejected by Ollama as non-tech → flagged for human moderation.

---

## ML Model Stack

| Component | Model Identifier | Architecture | Purpose | Size |
|-----------|-----------------|--------------|---------|------|
| **Toxicity** | `unitary/toxic-bert` | BERT (110M params) | Multi-label toxicity + threat checking | ~420 MB |
| **Hate Speech** | `Hate-speech-CNERG/dehatebert-mono-english` | BERT (110M params) | Dedicated hate speech validation | ~420 MB |
| **Tech Context** | `cross-encoder/nli-deberta-v3-base` | DeBERTa V3 (86M params) | NLI-based tech vs. cyber-harm detection | ~350 MB |
| **Semantic Analyzer** | `all-MiniLM-L6-v2` | Sentence Transformer (22M params) | Context-aware tech relevance via embeddings | ~80 MB |
| **Tech Visuals** | `openai/clip-vit-base-patch32` | CLIP / ViT (~150M params) | Tech image relevance scoring | ~600 MB |
| **Visual NSFW** | `Falconsai/nsfw_image_detection` | ViT (86M params) | Explicit imagery detection | ~340 MB |
| **Linguistics & NER** | `spacy: en_core_web_sm` | CNN (Trigram) | Entity extraction for cyber threat patterns | ~15 MB |
| **LLM Judge** | `llama3.2` (via Ollama) | Llama 3.2 (3B params) | Tech relevance judgement (Approach 2 only) | ~2 GB |

All models use a **Lazy Loading Singleton** pattern (`model_loader.py`) — each model only consumes memory when first needed and initializes exactly once per worker process.

---

## Frontend Dashboard

The frontend is a premium SaaS-grade dashboard built with **React 19**, **Tailwind CSS 4**, **Framer Motion**, and **Recharts**. It features four core views accessible via an animated kebab navigation menu:

### 📊 Analytics Page
Real-time content flow visualization with **8 interactive chart types**:
- Posts overview (Bar chart — allowed vs. blocked over 7 days)
- Content flow analysis (Sankey diagram — Input → AI Check → Allow/Block/Review)
- Content category breakdown (Treemap — Safe/Spam/Abuse/Sensitive)
- Banned words distribution (Donut chart)
- Trending topics tracker (Multi-line chart)
- Hourly activity volume (Area chart)
- Engagement trends + Content type distribution (mobile-only additions)

Each chart is expandable to a full-screen modal with rich tooltips and smooth spring animations. Auto-refreshes every 30 seconds.

### 📈 Metrics Dashboard
A comprehensive ML model observability panel with **22 specialized widget components**:
- **Model Cards** — Health status, version, and load state for each ML model
- **System Health** — Pipeline uptime, memory usage, and inference latency
- **Confusion Matrix** — True/false positive/negative visualization
- **Confidence Distribution** — Score histograms across all models
- **Toxicity Breakdown** — Per-category toxicity score visualization
- **Hate Speech Metrics** — dehatebert model-specific performance
- **Semantic Relevance Graph** — Tech vs. off-topic similarity scatter
- **Pipeline Latency** — End-to-end processing time breakdown
- **Recent Predictions Table** — Live feed of latest moderation decisions
- **Top Trigger Keywords** — Most frequently flagged terms
- **Edge Case Detector** — Borderline posts near decision thresholds
- **Model Agreement** — Cross-model consensus visualization
- And more: False Positive Indicator, Image Analysis Metrics, Prediction Volume, Category Breakdown, Time Series, Dashboard Filters

### 🛡️ Human Moderation Page
A purpose-built admin review queue for posts flagged by the AI pipeline:
- **Queue strip** — Horizontal scrollable preview cards with priority badges
- **Post review card** — Full post display with attached media, AI flagging reasons, and original moderation reasons
- **AI Insights panel** — Circular tech-score gauge, category/priority badges, borderline score breakdowns, and detection flags
- **Action controls** — Approve / Reject / Send for Edit with mandatory reason selection
- Connected to `/api/review/pending` and `/api/review/decide` endpoints; decisions persist to MongoDB

### 📰 Feed Page
A Twitter-style infinite-scrolling post feed with:
- Create Post form (text + image upload)
- Allowed posts render with clean styling
- Blocked posts display with red accent and rejection reasons
- Infinite scroll pagination via `usePosts` custom hook

**Additional UI Features:**
- 🌗 Light/Dark mode toggle with system preference detection
- 🎨 Glassmorphism elements, backdrop blur, and smooth spring transitions
- 📱 Fully responsive (mobile → desktop)
- 🔄 Framer Motion `AnimatePresence` for page transitions

---

## API Reference

### Posts — `/api/posts`
| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/posts/` | Create post (text + optional image) → synchronous moderation |
| `GET` | `/api/posts/` | Get all posts (paginated: `?skip=0&limit=50`) |
| `GET` | `/api/posts/{id}` | Get single post |
| `DELETE` | `/api/posts/{id}` | Delete post |
| `POST` | `/api/posts/{id}/reprocess` | Re-run moderation on existing post |

### Human Review — `/api/review`
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/review/pending` | Fetch all posts flagged for human review |
| `POST` | `/api/review/decide` | Submit approve/reject decision with reason |

### Metrics — `/api/metrics`
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/metrics/models` | Aggregated metrics for all ML models |
| `GET` | `/api/metrics/language-distribution` | Language breakdown of processed posts |
| `GET` | `/api/metrics/category-breakdown` | Content category distribution |
| `GET` | `/api/metrics/recent-predictions` | Latest N moderation decisions |
| `GET` | `/api/metrics/system-health` | System health summary |
| `GET` | `/api/metrics/advanced` | Comprehensive dashboard metrics |

### System
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Root — system info |
| `GET` | `/health` | Health check + active moderation approach |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc documentation |

---

## Project Structure

```
combined_Approach/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── posts.py                    # Post CRUD + moderation endpoints
│   │   │   ├── metrics.py                  # ML metrics API
│   │   │   └── moderation_review.py        # Human review endpoints
│   │   ├── core/
│   │   │   └── config.py                   # Pydantic settings
│   │   ├── db/
│   │   │   └── mongodb.py                  # MongoDB connection + repositories
│   │   ├── ml/
│   │   │   ├── multitask_model.py          # Ensemble moderator (Approach 1)
│   │   │   ├── ollama_moderator.py         # Ollama LLM moderator (Approach 2)
│   │   │   ├── semantic_analyzer.py        # Sentence Transformer tech scoring
│   │   │   ├── clip_model.py               # CLIP image-text analysis
│   │   │   ├── efficientnet_model.py       # NSFW image detection
│   │   │   ├── intent_entity_filter.py     # spaCy NER + intent detection
│   │   │   ├── tech_context_filter.py      # DeBERTa zero-shot NLI
│   │   │   ├── model_loader.py             # Lazy loading singleton manager
│   │   │   ├── preprocessing.py            # Text/image preprocessing
│   │   │   ├── text_normalizer.py          # Obfuscation/Hindi normalization
│   │   │   └── stubs.py                    # ML stub fallbacks (no GPU)
│   │   ├── schemas/                        # Pydantic request/response models
│   │   ├── services/
│   │   │   ├── moderation_service.py       # Approach router (ensemble ↔ ollama)
│   │   │   ├── _moderation_service_ensemble.py  # Full ensemble pipeline
│   │   │   ├── _moderation_service_ollama.py    # Ollama pipeline
│   │   │   ├── rule_engine.py              # Deterministic rule engine (~55KB)
│   │   │   ├── decision_engine.py          # Final verdict aggregator
│   │   │   ├── explanation_builder.py      # Human-readable reason generator
│   │   │   ├── text_processor.py           # Text processing utilities
│   │   │   ├── url_extractor.py            # URL analysis + risk scoring
│   │   │   └── metrics_repository.py       # Prediction metrics storage
│   │   ├── utils/
│   │   │   └── logger_utils.py             # Colored logging utility
│   │   └── main.py                         # FastAPI application entry
│   ├── tests/
│   │   ├── test_api.py                     # API endpoint tests
│   │   └── test_hindi_detection.py         # Hindi abuse detection tests
│   ├── models/                             # Cached ML model weights
│   ├── uploads/                            # User-uploaded images
│   ├── requirements.txt                    # Python dependencies
│   └── .env.example                        # Environment template
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   ├── AnalyticsPage.jsx           # 8-chart analytics dashboard
│   │   │   ├── MetricsDashboardPage.jsx    # ML metrics wrapper
│   │   │   ├── HumanModerationPage.jsx     # Admin review queue
│   │   │   └── FeedPage.jsx                # Post feed + create
│   │   ├── components/
│   │   │   ├── ModelMetrics/               # 22 specialized metric widgets
│   │   │   ├── CreatePost.jsx              # Post creation form
│   │   │   ├── PostCard.jsx                # Feed post card
│   │   │   ├── KebabMenu.jsx              # Animated navigation menu
│   │   │   ├── Loader.jsx                  # Loading spinner
│   │   │   └── Toast.jsx                   # Notification toasts
│   │   ├── hooks/
│   │   │   ├── usePosts.js                 # Feed state management
│   │   │   ├── useModeration.js            # Moderation queue hook
│   │   │   └── useAuth.js                  # Auth state hook
│   │   ├── services/
│   │   │   ├── api.js                      # Axios base instance
│   │   │   ├── postService.js              # Post API calls
│   │   │   ├── moderationService.js        # Review API calls
│   │   │   ├── metricsService.js           # Metrics API calls
│   │   │   └── authService.js              # Auth API calls
│   │   ├── context/
│   │   │   └── ThemeContext.jsx            # Light/Dark mode provider
│   │   ├── App.jsx                         # Root component + routing
│   │   ├── App.css                         # Global styles
│   │   ├── index.css                       # Tailwind entry + CSS variables
│   │   └── main.jsx                        # React DOM entry
│   ├── package.json
│   └── vite.config.js
│
├── docs/
│   ├── project_overview.md                 # Architecture documentation
│   └── FULL_PROJECT_DOCUMENTATION.pdf      # Comprehensive PDF docs
│
└── graphify-out/                           # Generated knowledge graph
    ├── GRAPH_REPORT.md                     # 695 nodes, 873 edges analysis
    ├── graph.html                          # Interactive graph visualization
    └── graph.json                          # Raw graph data
```

---

## Installation & Setup

### Prerequisites

| Dependency | Version | Required |
|------------|---------|----------|
| [Python](https://www.python.org/) | 3.10+ | ✅ |
| [Node.js](https://nodejs.org/) | 18+ | ✅ |
| [MongoDB](https://www.mongodb.com/try/download/community) | 7.0+ | ✅ (default port `27017`) |
| [Ollama](https://ollama.com/) | Latest | ⚠️ Only for Approach 2 |
| NVIDIA GPU (CUDA) | — | 🔶 Optional (CPU works, GPU accelerates) |

### 1. Backend Setup

```bash
# Navigate to backend
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# Install dependencies (includes PyTorch, Transformers, CLIP, etc.)
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your MongoDB URL and moderation approach

# Start the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

> **Note:** First startup will download ~2.2 GB of ML model weights from HuggingFace. Subsequent starts use cached weights.

### 2. Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start the Vite dev server
npm run dev
```

The frontend will be available at `http://localhost:5173` with API proxy to port `8000`.

### 3. Ollama Setup (Approach 2 Only)

```bash
# Install Ollama from https://ollama.com/

# Pull the Llama 3.2 model
ollama pull llama3.2

# Verify Ollama is running
curl http://localhost:11434/api/tags
```
---

## Resource Footprint

### Memory (RAM)

| State | RAM Usage |
|-------|-----------|
| Cold start (no models loaded) | ~200 MB |
| All models loaded (Ensemble approach) | **~2.2 – 2.6 GB** |
| Ollama approach (Rule Engine + Llama 3.2) | ~2.5 GB VRAM / ~4 GB RAM |

### CPU / GPU

| Operation | CPU Time | GPU (CUDA) Time |
|-----------|----------|-----------------|
| Text moderation (toxic-bert + DeBERTa) | 50–200 ms | < 15 ms |
| Image analysis (CLIP + NSFW ViT) | 200–600 ms | < 15 ms |
| Semantic embedding (MiniLM) | 20–50 ms | < 5 ms |
| Ollama LLM inference | 1–5 sec (CPU) | 200–500 ms |

### Scaling

1. **Horizontal:** `uvicorn --workers 2` (ensure `2.5GB × workers` RAM available)
2. **GPU:** Deploy on AWS `g4dn.xlarge` or equivalent with NVIDIA T4
3. **Fallback:** `FallbackModerator` in `multitask_model.py` routes through lightweight regex when ML models fail to load

---

## Contributors

<table>
  <tr>
    <td align="center"><strong>Girish</strong></td>
    <td align="center"><strong>Kartik</strong></td>
    <td align="center"><strong>Aniya</strong></td>
  </tr>
</table>

---

## Documentation

- 📄 [Architecture & Workflow Overview](docs/project_overview.md) — Pipeline workflow, model details, and resource footprint
- 📊 [Full Project Documentation](docs/FULL_PROJECT_DOCUMENTATION.pdf) — Comprehensive PDF covering all system components
- 🔗 [Knowledge Graph](graphify-out/graph.html) — Interactive visualization of 695 nodes and 873 edges mapping the entire codebase architecture (generated via Graphify)

---

## License

This project is developed as part of the **Loops** platform. All rights reserved.
