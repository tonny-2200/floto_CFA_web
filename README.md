# Floto Project

AI-powered conversion funnel analyzer for landing pages.

It audits a URL, captures page content + screenshot, generates funnel scores and recommendations, and can email a PDF report.

For full architecture and technical deep dive, see `NOTES.md`.

## Quick Start (Containerized)

### 1) Prerequisites
- Docker Desktop installed and running
- `docker compose` available

### 2) Create env files

Create `backend/.env` with:

```env
AZURE_ENDPOINT=your_azure_endpoint
AZURE_API_KEY=your_azure_api_key
GOOGLE_API_KEY=your_google_api_key
RESEND_KEY=your_resend_key
```

Create `frontend/.env.local` (optional for compose, but safe to keep):

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### 3) Run the app

From project root:

```bash
docker compose up --build
```

### 4) Open the app
- Frontend: `http://localhost:3000`
- Backend health check: `http://localhost:8000/health`

### 5) Stop containers

```bash
docker compose down
```

## What You Get
- URL audit via web UI
- AI-generated funnel stage analysis
- Actionable recommendations
- Optional emailed PDF report

For complete system flow, AI orchestration, and internal module documentation, refer to `NOTES.md`.
