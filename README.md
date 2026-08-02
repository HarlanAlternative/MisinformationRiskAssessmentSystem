# Misinformation Risk Assessment System

Misinformation Risk Assessment System is an end-to-end full-stack ML application for assessing the credibility risk of short claims and social-media style statements.

It combines a React frontend, a .NET 8 API, a FastAPI DistilBERT service, and classical ML models built with TF-IDF, Logistic Regression, and Random Forest.

## What It Does

- Runs a hybrid inference pipeline across Logistic Regression, Random Forest, and DistilBERT
- Returns a final risk level, confidence score, explanation, and model signals
- Stores analysis history through EF Core
- Supports local development, Docker Compose, and Azure-oriented deployment assets

## Stack

| Layer | Technology |
| --- | --- |
| Frontend | React, Vite, React Router |
| Backend | ASP.NET Core Web API, .NET 8 |
| Classical ML | Python, scikit-learn, TF-IDF, Logistic Regression, Random Forest |
| Transformer Service | FastAPI, HuggingFace Transformers, PyTorch |
| Persistence | EF Core, Azure SQL or InMemory fallback |
| Infra | Docker Compose, Bicep, GitHub Actions |
| Dataset | LIAR |

## Architecture

```text
Frontend (React SPA)
        |
        v
Backend (.NET 8 API)
  |               |
  v               v
Classical ML    BERT Service
  \               /
   \             /
    v           v
    Hybrid scoring + persistence
```

The backend is the orchestration boundary. It extracts heuristic signals, calls the classical Python scorer, calls the DistilBERT service, combines those outputs into a hybrid score, and persists the result.

For a deeper system walkthrough, see [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Repository Layout

```text
backend/
frontend/
bert_service/
scripts/
infra/
docs/
```

## Local Quick Start

### Prerequisites

- .NET 8 SDK
- Node.js 20+ and npm
- Python 3.11 recommended

### One-command local setup

Windows PowerShell:

```powershell
.\scripts\train_all.ps1
.\scripts\dev_start.ps1
```

macOS/Linux:

```bash
./scripts/train_all.sh
./scripts/dev_start.sh
```

### Manual local run

1. Copy the environment template.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

2. Install dependencies.

Windows PowerShell:

```powershell
python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -r .\backend\Services\Ml\requirements.txt
& .\.venv\Scripts\python.exe -m pip install -r .\bert_service\requirements.txt
npm.cmd --prefix .\frontend install
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/Services/Ml/requirements.txt
python -m pip install -r bert_service/requirements.txt
npm --prefix frontend install
```

3. Prepare the dataset and model artifacts.

```text
scripts/setup_liar_dataset.py
backend/Services/Ml/train_classical_models.py
bert_service/train.py --mode train
```

`--mode train` fine-tunes DistilBERT on LIAR and takes roughly 15 minutes on CPU. `--mode pretrained` is far quicker but installs an SST-2 sentiment checkpoint purely as a startup placeholder; it is unrelated to this task, scores below chance on it, and must never be benchmarked or reported. Model artifacts are not tracked in git, so this step is required after a fresh clone.

4. Start services.

- `bert_service` on `http://localhost:8001`
- backend on `http://localhost:5000`
- frontend on `http://localhost:5173/analyzer`

## Docker

Docker support is additive. It does not replace the local development scripts.

```bash
docker compose up --build
```

Default ports:

- frontend: `5173`
- backend: `5000`
- bert_service: `8001`

## API

| Method | Route | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Dependency and runtime health |
| `POST` | `/api/analyze` | Run the hybrid misinformation assessment |
| `GET` | `/api/history` | Return recent analysis records |
| `GET` | `/api/result/{id}` | Return a stored analysis result |

Example:

```bash
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The COVID-19 vaccine contains microchips for tracking",
    "content": "A viral post claims governments embedded tracking chips in vaccines.",
    "source": ""
  }'
```

## Hybrid Scoring

The ensemble base score is:

```text
0.00 * Logistic Regression
+ 0.55 * Random Forest
+ 0.45 * DistilBERT
```

The backend then applies small interpretable rule-based adjustments for factors such as missing source, exaggeration cues, emotional language, and limited context.

Weights live in `backend/appsettings.json` under `MachineLearning:HybridWeights`, and `scripts/evaluate_hybrid.py` reads that same file, so a benchmark cannot report a weighting the service is not applying. They were selected by `scripts/tune_hybrid_weights.py`, which grid-searches the weight simplex against validation ROC AUC and never reads the test split.

Logistic Regression carries zero weight: it is weaker than the Random Forest and largely redundant with it, since both run over the same TF-IDF features. It is still scored, because the explanation path uses its coefficients to surface top terms.

## Benchmark

The repository includes benchmark and evaluation scripts for:

- Logistic Regression
- Random Forest
- DistilBERT
- Hybrid Model

Current results on the LIAR test split are kept in [reports/benchmark.md](reports/benchmark.md), regenerated by the command below rather than transcribed here, so they cannot drift from the models that produced them.

Run:

Windows PowerShell:

```powershell
.\scripts\run_benchmark.ps1
```

macOS/Linux:

```bash
./scripts/run_benchmark.sh
```

Outputs:

- `reports/benchmark.json`
- `reports/benchmark.md`
- `reports/benchmark.csv`

## Azure and Infra

The deployed architecture runs all three services as Azure Container Apps scaled to zero, with images published to GitHub Container Registry:

- frontend, backend and bert_service on Azure Container Apps, `min-replicas 0`
- images on `ghcr.io`, built by the workflows in `.github/workflows/`
- persistence on Azure SQL, free serverless tier
- the frontend is the only public entry point; nginx proxies `/api` to the backend, and the BERT service uses internal ingress

The frontend runs as a container rather than on Static Web Apps because Static Web Apps operates only in Central US, East US 2, West US 2, West Europe and East Asia, none of which this subscription's region policy permits. Serving it through nginx turned out to suit the project better anyway: the browser stays on one origin, so no CORS configuration is needed and the backend address is never exposed to it.

This shape was chosen for cost. Azure Container Registry has no free tier, and the free App Service plan cannot host containers at all, so the original ACR plus App Service B1 arrangement carried a standing charge of roughly USD 18 a month. Public images on ghcr.io are free, and Container Apps scaled to zero cost nothing while idle.

### Building and deploying

Images build automatically on push. Each workflow fetches the model bundles from the artifact release and verifies them against their manifests, so an image cannot be published with weights that do not match the recorded fingerprint.

Infrastructure is provisioned once. The script is idempotent, so re-running it after a partial failure is safe:

```powershell
.\scripts\provision_azure.ps1
```

It creates the resource group, the Container Apps environment, and an Azure SQL database on the free serverless tier, then stores the connection string as a Container App secret. The database is set to pause rather than bill when the monthly free allocation runs out, so it cannot quietly consume credit. The generated SQL password is printed once; the backend never needs it again, since it reads the connection string from the secret.

Deployment is a separate step, and rolls out images without touching infrastructure:

```powershell
.\scripts\deploy_azure.ps1                # deploy the 'latest' images
.\scripts\deploy_azure.ps1 -ImageTag 4f2c1ab   # deploy a specific commit
```

Deployment is not part of any workflow on purpose. Authenticating a workflow to Azure requires a service principal, which requires an app registration, and the tenant this subscription belongs to sets `allowedToCreateApps` to false. Running deployment against a local `az login` also keeps a long-lived Azure credential out of repository secrets.

The BERT service uses internal ingress and is not reachable from outside the Container Apps environment; only the backend calls it. Note that the backend must address it over `https` — Container Apps ingress redirects plain http, and a redirected POST is downgraded to GET.

Both apps scale to zero, so the first request after an idle period pays a cold start of roughly a minute while the image is pulled and DistilBERT loads.

## Troubleshooting

### Backend startup validation fails

Check:

- `MachineLearning__PythonExecutable`
- `backend/Services/Ml/classical_predict.py`
- `backend/Services/Ml/artifacts`
- `BertService__Url`

### Frontend cannot call the API

Check:

- `VITE_API_BASE_URL`
- backend health at `/api/health`
- CORS settings when running cross-origin

### BERT service cannot load a model

Point `BERT_MODEL_DIR` to a prepared local checkpoint or allow the fallback HuggingFace download.

## Future Work

- Better calibration and threshold tuning
- Richer observability and latency reporting
- Stronger CI/CD for cloud deployment
- Batch inference and async jobs
- Authenticated multi-user history
