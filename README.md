<div align="center">

# 📱 Samsung Spec Desk

### Phone Query & Review System — scraping · RAG chatbot · multi-agent reviews · REST API

An intelligent system that scrapes Samsung smartphones from GSMArena, answers
natural-language questions about them with a grounded RAG chatbot, generates
product reviews through a two-agent CrewAI pipeline, and serves everything
through a FastAPI web interface.

Built as a personal project exploring **web scraping, RAG, and multi-agent
systems** — designed to be reproducible with a single command.

**Docker · FastAPI · PostgreSQL · BeautifulSoup · ChromaDB · CrewAI · Groq**

</div>

---

## ✨ Features

| Capability | What's here |
|---|---|
| **1. Web scraping** | 23 Samsung models scraped live from GSMArena (S26 Ultra → A07) — dynamic slug discovery, per-phone validation, 28+ spec fields, upserted into PostgreSQL |
| **2. Conversational chatbot** | Hybrid retrieval (exact entity matching + semantic search over ChromaDB) feeding a Groq-hosted open-source LLM — answers cite exact numbers, never invent specs |
| **3. Multi-agent system** | CrewAI crew: **Spec Retriever** (queries PostgreSQL through a custom tool) → **Review Writer** (drafts the review from the datasheet alone) |
| **4. API integration** | FastAPI with `/ask`, `/review`, `/phones` endpoints, Swagger docs at `/docs`, plus the Spec Desk web UI |

**Extras beyond the brief:**

- 🖥️ **Spec Desk UI** — catalog rail, pinned query desk, and a "receipts" rail showing exactly which datasheets grounded each answer (yellow-highlighted)
- 🧪 **21 passing tests** — parser (against a real GSMArena HTML fixture), database, retriever, agent tool, API
- 📦 **Offline fallback dataset** — the full 23-phone snapshot ships in the repo, so the demo works even if GSMArena rate-limits you
- 🛡️ **Graceful degradation** — no Groq key? The chatbot still answers from retrieval; the review pipeline falls back to a grounded template

---

## 🚀 Quick start

```bash
# optional: enable generative answers (free key: https://console.groq.com)
export GROQ_API_KEY=gsk_...          # Windows: set GROQ_API_KEY=gsk_...

docker compose up --build
```

Open **http://localhost:8000** — the catalog seeds automatically from the
bundled dataset, and the count badge should read **23 phones**.

> The web UI, chatbot, and catalog all work **without an API key**
> (retrieval-only mode). Add the key for LLM-generated answers and
> agent-written reviews.

---

## 🖥️ Run natively

Requires Python 3.11+ and any PostgreSQL server.

```bash
python -m venv .venv
.venv\Scripts\activate              # Windows
pip install -r requirements.txt

copy .env.example .env              # edit credentials + GROQ_API_KEY

python -m uvicorn api.main:app --reload
```

Default connection: `localhost:5433` → database `samsung_phones`
(override via `.env`). If your Postgres runs on the standard port, just set
`POSTGRES_PORT=5432`.

---

## 🕷️ Scraping live data

```bash
python -m scraper                   # or: docker compose run app python -m scraper
```

The scraper:

1. **Discovers slugs dynamically** from GSMArena's Samsung brand pages —
   no fragile hand-copied URLs
2. **Validates every page** — if the fetched page's title doesn't match the
   requested model, the record is rejected (never stores the wrong phone)
3. **Extracts extensive specs** — display, chipset, CPU/GPU, cameras + video
   modes, battery + charging speeds, connectivity, sensors, dimensions, SAR
   values, model numbers, colors, and benchmark scores (AnTuTu, GeekBench)
4. **Upserts idempotently** — re-running never duplicates; the fallback
   dataset is refreshed too

Politeness: a 2-second delay between requests and a descriptive User-Agent.

<details>
<summary><b>📦 The 23-model catalog</b></summary>

Galaxy S26 Ultra · S26+ · S26 · S26 FE · S25 · S24 Ultra · S24+ · S24 ·
S23 Ultra · S23 · S22 Ultra · S22 · S21 Ultra · S21 ·
Z Fold6 · Z Flip6 · Z Fold5 · Z Flip5 ·
A57 · A55 · A35 · A17 · A07

</details>

---

## 🔌 API reference

Interactive Swagger docs: **http://localhost:8000/docs**
(importable into Postman via `http://localhost:8000/openapi.json`)

| Method | Path | Body | Returns |
|---|---|---|---|
| `GET` | `/api/phones` | — | all phones with full specs |
| `GET` | `/api/phones/{name}` | — | one phone (fuzzy match) · 404 if unknown |
| `POST` | `/api/ask` | `{"query": "..."}` | `{"answer", "sources"}` — grounded LLM answer |
| `POST` | `/api/review` | `{"phone": "..."}` | `{"review", "specs_used", "phone"}` — agent pipeline |

### Sample queries

```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the camera specs of the Samsung Galaxy S23?"}'
# → {"answer": "...50 MP, f/1.8, 24mm (wide)...", "sources": ["Galaxy S23"]}

curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "Which Samsung phone has the best battery life?"}'
# → verdict across the catalog, sources = 8 phones

curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "How does the Galaxy S23 compare to the S22 in terms of performance?"}'
# → comparison table, sources = ["Galaxy S22 5G", "Galaxy S23"]
```

---

## 🧠 How grounding works

The chatbot uses a **hybrid retrieval pipeline** so answers stay exact:

```
                    ┌────────────────────────────────┐
"What camera specs  │ 1. ENTITY PASS                │
 does the S23 have?"│    "s23" → Galaxy S23 resolved │
        ─────────►  │    against the real catalog    │
                    │                                │
                    │ 2. SEMANTIC PASS (fallback)    │
                    │    ChromaDB top-k over         │
                    │    MiniLM embeddings           │
                    │                                │
                    │ 3. BEST-OF / COMPARISON PASS   │
                    │    "best battery" / "X vs Y"   │
                    │    pulls the relevant sheets   │
                    └───────────────┬────────────────┘
                                    ▼
                    spec sheets injected as context
                                    ▼
                    Groq LLM (gpt-oss-20b) answers
                    using ONLY those numbers
                                    ▼
                    {"answer": ..., "sources": [...]}
                                    ▼
                    UI renders the sources as
                    yellow-highlighted "receipts"
```

The `sources` field in every response is the proof of grounding — the UI
displays those datasheets in the receipts rail.

---

## 🤖 Multi-agent pipeline

```
POST /api/review {"phone": "Galaxy S23"}
        │
        ▼
┌──────────────────┐      ┌──────────────────────────┐
│  SPEC RETRIEVER  │ ──► │      REVIEW WRITER       │
│  (CrewAI agent)  │      │      (CrewAI agent)      │
│                  │      │                          │
│ phone_spec_tool  │      │ drafts Overview /        │
│ queries the      │      │ Display / Performance /   │
│ PostgreSQL DB    │      │ Cameras / Battery /      │
│                  │      │ Verdict — from the       │
└──────────────────┘      │ datasheet alone          │
                          └──────────────────────────┘
```

The writer agent only ever sees the retrieved specification sheet, so it
**cannot invent numbers**. The UI shows both agents as visible pipeline
steps while the review is generated.

---

## 🗂️ Project structure

```
├── api/                  FastAPI app
│   ├── main.py           endpoints + startup seeding
│   └── static/           Spec Desk UI (no build step)
├── agents/               CrewAI review pipeline
│   └── crew.py           Spec Retriever + Review Writer
├── chatbot/
│   ├── retriever.py      hybrid entity + semantic retrieval
│   └── chatbot.py        Groq LLM chain + model auto-detection
├── database/
│   ├── schema.sql        phones + specifications tables
│   └── db.py             connection, upserts, queries
├── scraper/
│   ├── gsmarena.py       dynamic scraper + slug discovery + validation
│   ├── models.py         PhoneRecord dataclass
│   └── __main__.py       CLI entrypoint (python -m scraper)
├── data/
│   └── fallback_dataset.json   23-phone snapshot (works offline)
├── tests/                21 pytest tests
├── docker-compose.yml    db + app, one command to run
└── Dockerfile            CPU-only torch (3.15 GB image)
```

---

## 🧪 Testing

```bash
python -m pytest tests/ -v     # 21 passed
```

Covers: the GSMArena parser (tested against a **real saved GSMArena page**,
no network needed), database upsert idempotency + fuzzy lookup (skips
gracefully if no Postgres), entity resolution (S23 vs S23+ vs S23 Ultra),
comparison splitting ("s23 vs s22 ultra" → both phones), the crew's spec
tool, and every API endpoint including 404s.

---

## 🔧 Troubleshooting

| Symptom | Fix |
|---|---|
| *"Generative mode is off"* | Set `GROQ_API_KEY` — free key at [console.groq.com](https://console.groq.com/keys) |
| Scraper reports failures | GSMArena rate-limiting — the DB keeps the fallback dataset; re-run to retry |
| API can't reach Postgres | Inside compose: `db:5432`. Natively: `localhost:5433` (compose maps the host port there since 5432 is often taken) |
| 400 `max_tokens` errors | Model limit — the app clamps to each model's limit automatically |

---

## 📋 What to check out

| Highlight | Where to see it |
|---|---|
| Data scraping: accuracy, completeness, structure | Run `python -m scraper` — 23/23 validated records, 28+ fields each, structured `phones` + `specifications` tables |
| Chatbot: diverse queries, relevant accurate responses | The three sample queries in the UI chips; check `sources` on each answer |
| Multi-agent: agents working together | POST `/api/review` — Retriever feeds Writer; watch the pipeline steps in the UI |
| API: seamless interaction, multiple queries | Swagger at `/docs`, Postman-importable spec, 404/422 handling |

---

<div align="center">

**Stack**: Python 3.11 · FastAPI · PostgreSQL · BeautifulSoup · ChromaDB ·
sentence-transformers · CrewAI · Groq (gpt-oss-20b / qwen3.8-27b) · Docker

</div>
