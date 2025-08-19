# Advanced Software Solution (ASS)

An intelligent, **real-time labeling service** that assigns labels to incoming JSON payloads using **user-defined rules**. It includes a clean web UI for configuring rules, a live **analytics dashboard**, and a **REST API** for programmatic ingestion.

Built for scenarios where **each user can have a different JSON schema** and **custom labeling requirements**. Stack: **Flask, SQLite/SQLAlchemy, Chart.js**, and a robust rule engine (comparison + logical operators with grouped conditions).

## What This Project Does

Turn arbitrary JSON streams into a **consistent, labeled data feed**:

- Configure rules with a web UI (keys, operators, values, labels, priority, enable/disable).

- Ingest JSON via `POST /api/process`; apply all matching rules in real time.

- View **statistics & charts** (totals, label breakdown) with live polling and CSV export.

- Support **per-user isolation** using `X-User-Id` header (rules/payloads/stats are scoped).

- Ship with **demo rules** (Chocolate pricing bands) for instant testing.

### Under the hood

- **Rule Engine** with operators `=, !=, <, >, <=, >=` and logical **AND/OR** (DNF: OR across groups of AND conditions).

- **Dot-path** access for nested JSON (e.g., `order.items[0].price`).

- **Flask REST API** powers both UI and external clients.



## Technical Stack Summary

| Layer             | Tools / Libraries                                      |
|------------------|--------------------------------------------------------|
| Web Framework | **Flask** |
| Database        | **SQLite**, **SQLAlchemy** |
| API Docs     | **flasgger** (Swagger UI at `/apidocs`) |
| Frontend       | Flask **Jinja** templates + **Bootstrap 5**|
| Charts   | **Chart.js**|
| Rule Engine         | Custom Python (operators + DNF grouping)|
| Testing| pytest |
| Deployment| **Gunicorn** + (Render) |

## Supported Input

- **JSON objects** (case-sensitive keys; `Price` != `price`).

- **Dot-paths** for nested fields (e.g., `order.total.amount`, `items[0].sku`).

- Multi-user via `X-User-Id` header; default is demo_user from the UI.

## Why Flask + SQLite?

- **Flask** keeps the stack simple (UI + API in one app) and matches the assignment’s “RESTful backend + web frontend” requirement.

- **SQLite** is **free** and file-based; perfect for demos and small deployments. Swap to Postgres by setting `DATABASE_URL` without changing code.

## How It Works (Architecture)

| Component             | Role                                                                 |
|------------------|----------------------------------------------------------------------|
| Frontend (UI)    | **Configuration** to build/validate rules; **Dashboard** for charts & CSV export.          |
| REST API    | `/api/rules` (CRUD/toggle), `/api/process`, `/api/statistics`, `/api/statistics/export`. |
| Rule Engine  | DNF evaluation: groups of AND conditions OR’ed together; applies **all** matches.  |
| Storage | Rules, conditions, payloads, labels (SQLite/SQLAlchemy).|
| Multi-user Scope | Every read/write filtered by `X-User-Id`.|

### Flow

1. Configure rules: saved via `/api/rules`.
   
2. Post payloads: `/api/process` applies active rules, stores payload+labels.

3. Dashboard polls `/api/statistics`: totals & breakdown (pie/bar), filters, CSV export.

## Key Features

- **Rule Builder:** Key extraction from sample JSON, operators `=, !=, <, >, <=, >=`, logical AND/OR, labels, priority, enable/disable.

- **Validation:** Basic type/operator checks on rule save; missing keys at process time just evaluate to **false**.

- **Real-time Processing:** Apply **all** matching rules; deterministic ordering by **priority** (lower = higher).

- **Analytics:** Totals, label breakdown with percentages; **live polling** and **CSV export**.

- **Multi-Tenant Ready:** Per-user isolation with `X-User-Id`.


## Project Structure

```text
Advanced Software Solution/
├── app/
│   ├── __init__.py        
│   ├── models.py 
│   ├── rule_engine.py 
│   ├── services.py 
│   ├── routes/ 
│   |   ├── api.py
|   |   └── pages.py
│   ├── templates/       
│   └── static/    
├── tests/
│   ├── test_rule_engine.py                
│   └── test_api.py                
├── instance/                                          
├── requirements.txt
├── run.py
├── wsgi.py 
└── README.md             
```

# Setup Instructions

## 1. Clone the repository

```bash
git clone <path to the git code>
cd Advanced-Software-Solution-ASS
```

## 2. Create & activate venv

```bash
python -m venv <env_name>
venv\Scripts\activate
```

## 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

## 4. Initialize database (SQLite)

```bash
python run.py --initdb
```

### (Optioinal) Load demo rules:

```bash
python run.py --loaddemo
```

## 5. Run locally

```bash
python run.py
```

## API Quickstart (from VS Code Terminal)

### Process a payload

### PowerShell

```bash
$body = @{ Product = "Chocolate"; Price = 1.8 } | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:5000/api/process" `
  -Headers @{ "X-User-Id" = "demo_user" } `
  -ContentType "application/json" `
  -Body $body
```

### curl.exe (Windows)

```bash
curl.exe -X POST "http://127.0.0.1:5000/api/process" `
  -H "Content-Type: application/json" `
  -H "X-User-Id: demo_user" `
  -d "{\"Product\":\"Chocolate\",\"Price\":1.8}"
```

### Statistics

```bash
Invoke-RestMethod -Method Get `
  -Uri "http://127.0.0.1:5000/api/statistics?label=Green" `
  -Headers @{ "X-User-Id" = "demo_user" }
```


## Sample Use Case

1. **Configure rules** (e.g., Chocolate bands):

    - `Product = "Chocolate" AND Price < 2 → Green (p=10)`

    - `Product = "Chocolate" AND 2 <= Price < 5 → Yellow (p=20)`

    - `Product = "Chocolate" AND Price >= 5 → Red (p=30)`

2. **Ingest payloads**

    - `{"Product":"Chocolate","Price":1.8} → Green`

    - `{"Product":"Chocolate","Price":3} → Yellow`

    - `{"Product":"Chocolate","Price":6} → Red`

3. **See analytics** on the Dashboard (totals, pie/bar charts) and **Export CSV**.


## Testing

Run the unit tests:

```bash
pip install pytest
python -m pytest -q
```

## Deployment (Render)

While deploying do label these columns as following:

- **Build Command:** `pip install -r requirements.txt`

- **Start Command:** `gunicorn wsgi:app --bind 0.0.0.0:$PORT --workers 2`

- **Environment Variables:**
  - `SECRET_KEY` = any string
  - `SEED_DEMO` = true


## Summary

This project provides a **complete, rule-driven labeling system** with:

- A friendly **web UI** to configure rules.

- A solid **REST API** to ingest and label JSON in real time.

- A live **dashboard** with charts and CSV export.

- **Per-user isolation** out of the box.