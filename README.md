# Threadline — Textile Sentiment Analysis & Business Intelligence

## Project structure

```text
backend/              FastAPI API, authentication, NLP, scoring, MongoDB setup
  main.py
  db.py
frontend/             Bootstrap/Chart.js web interface
  static/index.html
  static/app.js
  static/style.css
```

FastAPI + Bootstrap + Chart.js application for textile review intelligence. It includes JWT authentication, RBAC, rule-based ABSA, emotion analysis, fake-review flagging, complaint classification, priority scoring, recommendations, seasonal/festival analytics, product drilldowns, and distinct role workspaces: Command Center, Design Studio, Growth Console, and Defect Watch.

## Run locally

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -r requirements.txt
py -m uvicorn backend.main:app --reload
```

Open http://127.0.0.1:8000. Demo password for all users is `demo123`.

Roles: `owner@textile.ai` (management), `design@textile.ai`, `sales@textile.ai` (marketing), and `qa@textile.ai`.

Swagger docs are available at `/docs`; health status is available at `/health`. The current demo reads the bundled JSON data and keeps new review mutations in memory. `backend/db.py` defines the production collections and indexes for a MongoDB-backed deployment.

## Run with Docker

```powershell
docker compose up --build
```

The API and frontend are served at http://127.0.0.1:8000. Configure `JWT_SECRET`, `MONGODB_URL`, `DATABASE_NAME`, and `LOG_LEVEL` through the Compose environment for a production-like run. When `MONGODB_URL` is configured, the app seeds MongoDB from `data/products.json` and `data/reviews.json` when the collections are empty, then persists new reviews in MongoDB.

## Role workflows

- Management uses Command Center for department health and cross-functional risk.
- Design uses Design Studio for the visual collection gallery and design feedback board.
- Marketing uses Growth Console for seasonal momentum, campaign opportunities, and pricing signals.
- QA uses Defect Watch for severity-ranked negative review alerts and defect patterns.

## Real Amazon Fashion data

The importer targets the official Amazon Fashion 5-core subset from the [UCSD/Julian McAuley Amazon Review Data page](https://nijianmo.github.io/amazon/index.html). The page lists the Amazon Fashion 5-core subset as 3,176 reviews and documents the source fields `reviewText`, `overall`, `asin`, and `reviewTime`. Run `python backend/import_amazon.py --download`, or place a downloaded `AMAZON_FASHION_5.json.gz` in `data/` and run `python backend/import_amazon.py`. The normalized output is loaded automatically on the next server restart.
