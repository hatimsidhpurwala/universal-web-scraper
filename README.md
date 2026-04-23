# 🕷️ Smart Web Scraper — RAG Pipeline + WhatsApp Bot

A production-grade AI-powered web scraper that scrapes websites, builds a semantic search index, and answers questions via a Streamlit UI or WhatsApp — built entirely on free tools.

---

## 📋 Table of Contents

- [Project Overview](#project-overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [How It Works](#how-it-works)
- [Setup & Installation](#setup--installation)
- [Running the App](#running-the-app)
- [WhatsApp Bot Setup](#whatsapp-bot-setup)
- [Deployment](#deployment)
- [Updating Website Data](#updating-website-data)
- [Environment Variables](#environment-variables)
- [Architecture Diagram](#architecture-diagram)

---

## 🧠 Project Overview

This project allows a business to scrape their own websites, index the content using vector embeddings, and let users ask questions — either through a Streamlit web app or directly on WhatsApp.

**Key capabilities:**
- Scrape entire websites (up to 100 pages) using Selenium
- Clean, chunk, and embed content into a vector database (Qdrant)
- Answer questions semantically using LangGraph agent + Groq LLM
- Accept voice messages (Groq Whisper transcription)
- Accept image messages (pytesseract OCR)
- Multi-turn conversation memory per user
- Pre-built index for instant answers — no scraping on every query

---

## 🛠️ Tech Stack

| Layer | Tool | Cost |
|---|---|---|
| Web Scraping | Selenium + BeautifulSoup | Free |
| HTML Cleaning | Custom cleaner.py | Free |
| Chunking | LangChain RecursiveCharacterTextSplitter | Free |
| Embedding Model | sentence-transformers (all-MiniLM-L6-v2) | Free, runs locally |
| Vector Database | Qdrant (local or cloud) | Free tier |
| LLM | Groq — llama-3.3-70b-versatile | Free tier |
| Voice Transcription | Groq Whisper | Free tier |
| Agent Framework | LangGraph | Free |
| Web UI | Streamlit | Free |
| WhatsApp Integration | Twilio Sandbox | Free (testing) |
| Cloud Deployment | Railway / Render | Free tier |
| Webhook Server | FastAPI + Uvicorn | Free |

> ✅ **Zero cost** to build, develop, and test this entire project.

---

## 📁 Project Structure

```
universal-web-scraper/
│
├── app.py                  ← Streamlit UI (Tab 1: Scrape, Tab 2: Q&A)
├── scraper.py              ← Selenium scraping + crawling + ingest pipeline
├── cleaner.py              ← 3-layer HTML cleaning (boilerplate, dedup, normalise)
├── chunker.py              ← LangChain text chunking (500 tokens, 50 overlap)
├── embedder.py             ← Sentence Transformers embedding (384-dim vectors)
├── vector_store.py         ← Qdrant vector DB (store + search chunks)
├── agent.py                ← LangGraph agent (retrieve → answer + memory)
├── whatsapp_webhook.py     ← FastAPI WhatsApp webhook (Twilio integration)
├── indexer.py              ← Admin tool: index all .md files into Qdrant
│
├── md_files/               ← Store scraped .md files here (one per website)
│   ├── site1.md
│   ├── site2.md
│   └── ...
│
├── qdrant_local/           ← Auto-created local vector DB (ignored by git)
├── requirements.txt        ← Python dependencies
├── Procfile                ← Railway/Render start command
├── Dockerfile              ← Docker deployment config
├── .env                    ← API keys (never commit this)
├── .env.example            ← Template for env variables
└── .gitignore
```

---

## ⚙️ How It Works

### RAG Pipeline (Retrieval-Augmented Generation)

```
SETUP PHASE (run once per website)
────────────────────────────────────
Scrape website (Selenium)
        ↓
Clean HTML (remove nav, footer, cookie banners)
        ↓
Chunk into 500-token pieces (LangChain)
        ↓
Embed each chunk → 384-dim vector (sentence-transformers)
        ↓
Store vectors + text in Qdrant
        ↓
Index is READY ✅

QUERY PHASE (instant, every time)
────────────────────────────────────
User asks a question
        ↓
Embed the question → vector
        ↓
Search Qdrant for top-8 most similar chunks
        ↓
Send chunks + question to Groq LLM
        ↓
Answer returned in seconds ⚡
```

### WhatsApp Flow

```
User sends WhatsApp message
        ↓
Twilio receives it → sends POST to your webhook URL
        ↓
FastAPI (whatsapp_webhook.py) receives message
        ↓
[Voice?] → Groq Whisper transcribes audio to text
[Image?] → pytesseract extracts text from image
        ↓
agent.ask() → Qdrant search → Groq LLM
        ↓
Answer sent back via Twilio → WhatsApp ✅
```

---

## 🚀 Setup & Installation

### Prerequisites
- Python 3.11 (required — 3.12+ breaks some ML libraries)
- Google Chrome installed
- Git

### Step 1 — Clone the repository
```bash
git clone https://github.com/hatimsidhpurwala/universal-web-scraper.git
cd universal-web-scraper
```

### Step 2 — Create Python 3.11 virtual environment
```bash
py -3.11 -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Mac/Linux
```

### Step 3 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Create `.env` file
```bash
copy .env.example .env
```
Then open `.env` and fill in your API keys (see [Environment Variables](#environment-variables)).

### Step 5 — Pre-index your websites (first time only)
Place your scraped `.md` files inside the `md_files/` folder, then run:
```bash
python indexer.py
```
This builds the full Qdrant vector index. Only needs to run once, or when website content changes.

---

## ▶️ Running the App

```bash
venv\Scripts\activate
streamlit run app.py
```

App opens at: `http://localhost:8501`

**Tab 1 — Scrape & Index:**
- Enter a website URL
- Set max pages to crawl
- Click "Scrape Full Website"
- The app scrapes, cleans, chunks, embeds, and stores into Qdrant automatically
- Download the `.md` file to reuse later (skip re-scraping)

**Tab 2 — Ask Questions:**
- Choose data source: Tab 1 data OR upload a saved `.md` file
- Type a question, record voice, or upload an image
- Get instant answers with source attribution

---

## 📱 WhatsApp Bot Setup

### Testing (Free — Twilio Sandbox)

1. Sign up at [twilio.com](https://twilio.com) — free account
2. Go to **Messaging → Try it out → Send a WhatsApp message**
3. Note your sandbox number: `+1 415 523 8886`
4. Save the number in your phone contacts
5. Send the join message shown on screen (e.g. `join yellow-tiger`) to activate
6. Copy your **Account SID** and **Auth Token** from the Twilio dashboard
7. Add them to your `.env` file
8. Deploy the webhook (see [Deployment](#deployment))
9. In Twilio Sandbox Settings, set webhook URL to:
   ```
   https://your-deployed-url.com/webhook
   ```
   Method: **HTTP POST**

> ⚠️ Every tester must send the join code once. This is the only limitation of the free sandbox.

### Production (Mentor's Paid WhatsApp API)

When moving to the real WhatsApp Business API, only 3 values change in `.env`:
```
TWILIO_ACCOUNT_SID = mentor's_production_sid
TWILIO_AUTH_TOKEN  = mentor's_production_token
TWILIO_WHATSAPP_NUMBER = whatsapp:+91XXXXXXXXXX
```
Everything else — the RAG pipeline, Qdrant, agent — stays identical.

---

## ☁️ Deployment

### Option A — Railway (Recommended)

1. Push code to GitHub
2. Go to [railway.app](https://railway.app) → Login with GitHub
3. New Project → Deploy from GitHub repo → select this repo
4. Add environment variables in Railway dashboard (Variables tab)
5. Railway auto-detects the `Dockerfile` and deploys
6. Get your public URL from Settings → Networking → Generate Domain
7. Test: `https://your-app.up.railway.app/health`

### Option B — Render

1. Go to [render.com](https://render.com) → Login with GitHub
2. New → Web Service → connect this repo
3. Settings:
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn whatsapp_webhook:app --host 0.0.0.0 --port $PORT`
   - **Instance Type:** Free
4. Add environment variables
5. Deploy

> **Note:** Render free tier sleeps after 15 min inactivity. Use [cron-job.org](https://cron-job.org) to ping `/ping` every 10 minutes to keep it awake.

### Option C — Mentor's Windows Server (Production)

```bash
# On the server
git clone https://github.com/hatimsidhpurwala/universal-web-scraper.git
cd universal-web-scraper
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

# Create .env with production keys
# Install as Windows Service using NSSM (nssm.cc)
nssm install WhatsAppBot
# Path: path\to\venv\Scripts\uvicorn.exe
# Args: whatsapp_webhook:app --host 0.0.0.0 --port 8000
nssm start WhatsAppBot
```

---

## 🔄 Updating Website Data

When a website's content changes:

```bash
# Re-scrape that site from Tab 1 → save new .md file to md_files/
# Then re-index only that one site:
python indexer.py site1.md

# To re-index all sites:
python indexer.py
```

No redeployment needed — Qdrant updates live.

---

## 🔑 Environment Variables

Create a `.env` file with these values:

```env
# LLM API
GROQ_API_KEY=your_groq_api_key

# Twilio WhatsApp
TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Qdrant Cloud (leave blank for local mode)
QDRANT_URL=https://your-cluster.aws.cloud.qdrant.io
QDRANT_API_KEY=your_qdrant_api_key

# Embedding mode (true = lightweight for cloud, false = full for local/production)
USE_FASTEMBED=false
```

Get your free API keys:
- **Groq:** [console.groq.com](https://console.groq.com)
- **Qdrant Cloud:** [cloud.qdrant.io](https://cloud.qdrant.io)
- **Twilio:** [twilio.com](https://twilio.com)

---

## 🗺️ Architecture Diagram

```
                        ┌─────────────────────────────────┐
                        │         Streamlit UI             │
                        │   Tab 1: Scrape  |  Tab 2: Q&A  │
                        └──────────┬──────────────┬────────┘
                                   │              │
                    ┌──────────────▼──┐    ┌──────▼───────────┐
                    │  Scraping Layer │    │   Agent Layer     │
                    │  Selenium       │    │   LangGraph       │
                    │  BeautifulSoup  │    │   + Memory        │
                    └──────────┬──────┘    └──────┬────────────┘
                               │                  │
              ┌────────────────▼──┐    ┌──────────▼────────────┐
              │  Cleaning Layer   │    │   Retrieval Layer      │
              │  cleaner.py       │    │   vector_store.py      │
              │  3-layer cleaning │    │   Qdrant search        │
              └────────────┬──────┘    └──────────┬────────────┘
                           │                      │
              ┌────────────▼──────┐    ┌──────────▼────────────┐
              │  Chunking Layer   │    │   Qdrant Vector DB     │
              │  chunker.py       │    │   (local or cloud)     │
              │  500 tok, 50 ovlp │    │                        │
              └────────────┬──────┘    └───────────────────────┘
                           │
              ┌────────────▼──────┐
              │  Embedding Layer  │
              │  embedder.py      │
              │  384-dim vectors  │
              └───────────────────┘

                    ┌──────────────────────────────────┐
                    │         WhatsApp Bot              │
                    │   User → Twilio → FastAPI         │
                    │   Voice (Whisper) / Image (OCR)   │
                    │   → agent.ask() → Groq LLM        │
                    │   → Answer → Twilio → User        │
                    └──────────────────────────────────┘
```

---

## 👨‍💻 Created By

**Hatim Sidhpurwala**

---

## 📄 License

This project is for internal/educational use. Not for public redistribution.
