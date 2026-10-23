# Wind Forecast Analytics

A decision-support pilot for a UK energy utility's day-ahead procurement team. The application uses Elexon BMRS national wind data to show which wind forecast was actually available at a historical decision point and how accurate that forecast proved to be.

## What it answers

- What wind generation forecast was available 24, 12, or 6 hours before each January 2026 delivery hour?
- How close was that forecast to realised national wind generation?
- How do forecast error, bias, and data coverage change as the forecast is refreshed nearer delivery?

The `latest` scenario is a near-delivery benchmark only. It is deliberately labelled as hindsight and is not a valid day-ahead decision view.

## Data and methodology

Data comes only from Elexon BMRS, as specified in the challenge:

- [WINDFOR forecast stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/WINDFOR/stream)
- [FUELHH actual generation stream](https://bmrs.elexon.co.uk/api-documentation/endpoint/datasets/FUELHH/stream), filtered to `fuelType=WIND`

WINDFOR forecasts are hourly; FUELHH actuals are half-hourly. For each hourly forecast delivery interval, the application calculates the mean of the complete `HH:00` and `HH:30` actual MW observations. It never duplicates a forecast to manufacture additional observations. Missing or conflicting actual intervals are withheld and reported through coverage rather than treated as zero.

For each delivery interval, the selected forecast is the latest forecast published at or before `delivery time - cutoff`. This prevents look-ahead bias.

Reported metrics:

- **MAE**: mean absolute error in MW.
- **RMSE**: root mean square error in MW; larger errors count more.
- **Bias**: mean forecast minus actual error; positive means over-forecasting.
- **WAPE**: total absolute error divided by total matched actual generation.
- **Coverage**: matched intervals divided by expected hourly delivery intervals.

## Repository layout

```text
backend/                 FastAPI API and analysis pipeline
  app/api/routes/        Health, analysis, and CSV export routes
  app/services/          Elexon client, normalization, vintage selection, metrics
  tests/                 Unit and API tests
frontend/                React + Vite dashboard
  src/api/               Typed API client
  src/components/        Live dashboard
  src/App.tsx            Frontend entry view
docker-compose.yml       Local Docker development environment
.env.example             Example backend configuration
```

## Run locally

Prerequisites: Docker Desktop for the container workflow, or Node.js 22+ for a locally-run frontend.

### All services with Docker

```powershell
docker compose up --build
```

Open the dashboard at `http://localhost:5173` and API documentation at `http://localhost:8000/docs`.

### Local frontend + Docker backend

```powershell
docker compose up backend
cd frontend
npm ci
npm run dev
```

The frontend defaults to `http://localhost:8000`. Override it when needed:

```powershell
$env:VITE_API_BASE_URL = "http://localhost:8000"
npm run dev
```

## Test and build

```powershell
docker compose run --rm backend pytest -q
cd frontend
npm run build
```

## API

- `GET /api/health`
- `GET /api/analysis?start_date=2026-01-01&end_date=2026-01-31&cutoff=24h`
- `GET /api/exports/analysis.csv?start_date=2026-01-01&end_date=2026-01-31&cutoff=24h`

Supported cutoffs are `24h`, `12h`, `6h`, and `latest`.

## Deployment

Deployment is not configured yet. Before submission, deploy the React frontend (for example, Vercel) and the Python backend to a container-compatible host, set `VITE_API_BASE_URL` to the public backend URL, and set `CORS_ORIGINS` to the deployed frontend origin. Test all submitted URLs in an incognito browser session.

## AI assistance disclosure

AI coding assistance was used to help implement and document this assignment. All design decisions, Elexon request behaviour, metric definitions, and application output were reviewed and validated with automated tests and a live January 2026 Elexon analysis.
