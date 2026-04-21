# Floto Project - System Notes

## What this system does

This project is an AI-powered **conversion funnel analyzer** for landing pages.

Given a URL, it:
- crawls and captures the page (content + screenshot),
- runs a multi-step AI audit pipeline,
- returns structured funnel scores and recommendations,
- and can generate + email a PDF report.

It is split into:
- `frontend` (Next.js UI),
- `backend` (FastAPI + crawler + AI orchestration),
- Docker setup (`docker-compose.yml`) to run both together.

---

## High-level architecture

### Frontend (`frontend`)
- Main UI lives in `frontend/app/page.tsx`.
- User enters URL and clicks **Run Audit**.
- Frontend sends request to internal Next API route: `POST /api/audit`.
- Next API route proxies to FastAPI backend `/audit`.
- UI renders:
  - overall score,
  - stage-wise funnel chart,
  - top recommendations,
  - captured screenshot.

Key proxy files:
- `frontend/app/api/audit/route.ts`
- `frontend/app/api/send-report/route.ts`

### Backend (`backend`)
- FastAPI entrypoint: `backend/src/app.py`
- Main endpoints:
  - `GET /health`
  - `POST /audit` (core pipeline)
  - `POST /send-report` (generate/send PDF separately)

Core backend modules:
- `backend/src/crawler.py` - captures page context.
- `backend/src/graph.py` - AI orchestration with LangGraph.
- `backend/src/prompts.py` - prompt templates.
- `backend/src/generate_pdf.py` - PDF creation + email send (Resend).

---

## End-to-end request flow

1. User submits URL in frontend.
2. Frontend calls `POST /api/audit` (Next route).
3. Next route forwards to backend `POST /audit`.
4. Backend crawler captures:
   - markdown content,
   - base64 screenshot,
   - structured UI elements.
5. Backend saves screenshot as `latest_audit_screenshot.png` (local artifact).
6. Backend runs AI audit graph (`run_audit` in `graph.py`).
7. Graph returns normalized report JSON:
   - `overall_score`,
   - `funnel_data` (Awareness/Exploration/Consideration/Conversion),
   - `top_recommendations`.
8. If `send_email=true`:
   - backend generates `report.pdf`,
   - backend emails it via Resend.
9. Frontend receives response and renders dashboard.

---

## AI orchestration

The AI logic is implemented as a **3-stage LangGraph pipeline** in `backend/src/graph.py`.

### 1) Mapper node (`mapper_node`)
Input:
- crawled markdown
- structured elements JSON

Goal:
- Map page evidence into funnel stages:
  - awareness
  - exploration
  - consideration
  - conversion

Output:
- structured funnel stage map (normalized JSON)

### 2) Auditor node (`auditor_node`)
Input:
- mapped funnel stages
- screenshot (sent as base64 image in multimodal prompt)

Goal:
- Detect friction points by combining text + visual layout understanding.

Output:
- list of friction points with:
  - stage
  - severity
  - issue
  - evidence
  - impact

### 3) Reporter node (`reporter_node`)
Input:
- funnel stage map
- friction points
- structured elements

Goal:
- Produce final dashboard JSON:
  - overall score
  - stage scores/status
  - top recommendations

Output hardening:
- parser removes markdown fences and safely parses JSON,
- schema normalization keeps response stable,
- score calibration blends LLM score with deterministic rules to reduce noisy swings.

### Model layer
- Primary model in flow: Azure OpenAI via `AzureChatOpenAI` (`gpt-5-mini` deployment).

### Why this orchestration is useful
- Multi-step decomposition improves consistency versus one-shot prompts.
- Explicit state passing (`GraphState`) keeps each stage focused.
- Post-processing/normalization protects UI from malformed LLM output.
- Deterministic score calibration makes scoring more reliable across runs.

---

## Reporting subsystem

In `backend/src/generate_pdf.py`:
- `generate_audit_pdf(report_data, output_path)` builds a styled PDF report.
- `send_audit_email(pdf_path)` sends that PDF using Resend API.

Current behavior:
- recipient email is hardcoded (`HARDCODED_REPORT_EMAIL`).
- `/audit` can send email inline when `send_email=true`.
- `/send-report` can also send from a provided report payload.

---

## Containerization and how to run

The app is containerized with `docker-compose.yml` and two Dockerfiles:
- `backend/Dockerfile`
- `frontend/Dockerfile`

### Services and ports
- `backend` -> `localhost:8000`
- `frontend` -> `localhost:3000`

Frontend container calls backend internally at:
- `FASTAPI_BASE_URL=http://backend:8000`

### Required environment files

Create these files before running:

1. `backend/.env`
   - `AZURE_ENDPOINT`
   - `AZURE_API_KEY`
   - `GOOGLE_API_KEY` (currently initialized in code)
   - `RESEND_KEY` (required for email sending)

2. `frontend/.env.local`
   - optional for compose run (compose already injects `FASTAPI_BASE_URL`)
   - can include `NEXT_PUBLIC_API_BASE_URL` if needed outside compose

### Run commands (from project root)

```bash
docker compose up --build
```

Then open:
- Frontend: `http://localhost:3000`
- Backend health: `http://localhost:8000/health`

Stop:

```bash
docker compose down
```

---

## Quick operational notes

- The backend writes local artifacts like `latest_audit_screenshot.png` and `report.pdf`.
- `depends_on` in compose ensures startup order, not backend readiness health checks.
- The frontend currently triggers email through `/audit` flow (not a separate UI step).
- No database persistence is used; output is generated per request.
