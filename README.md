# Misinformation Risk Assessment System

## Project Overview

Misinformation Risk Assessment System is an end-to-end full-stack application for assessing the credibility risk of short news claims and social-media style statements.

The project combines:

- a React frontend for claim submission and result visualization
- a .NET 8 Web API for orchestration, feature engineering, persistence, and hybrid scoring
- a FastAPI DistilBERT inference service for transformer-based semantic signals
- classical machine learning models built with TF-IDF, Logistic Regression, and Random Forest

The current implementation is designed as a portfolio-ready ML systems project that demonstrates practical model orchestration, explainability, API design, and full-stack deployment patterns.

## Key Features

- Hybrid three-model inference pipeline
- Weighted ensemble scoring across Logistic Regression, Random Forest, and DistilBERT
- Explainability output for both classical and transformer signals
- Full-stack workflow from UI submission to persisted result
- Local development support for Windows PowerShell and macOS/Linux shells
- EF Core persistence with Azure SQL or in-memory fallback for local development
- Swagger-enabled backend API for easy inspection and testing

## System Architecture

```text
+----------------------+
| Frontend (React)     |
| Vite SPA             |
+----------+-----------+
           |
           v
+-------------------------------+
| Backend (.NET 8 Web API)      |
| - request validation          |
| - feature engineering         |
| - hybrid scoring              |
| - persistence orchestration   |
+-----+-------------------+-----+
      |                   |
      |                   |
      v                   v
+-------------------+   +-----------------------------+
| Classical ML      |   | BERT Service                |
| Python + sklearn  |   | FastAPI + Transformers      |
| TF-IDF artifacts  |   | DistilBERT inference        |
| LR + RF           |   | salient token extraction    |
+-------------------+   +-----------------------------+
      \                   /
       \                 /
        \               /
         v             v
+----------------------------------------------+
| Persistence                                   |
| EF Core / Azure SQL or InMemory (local dev)   |
+----------------------------------------------+
```

### Runtime Flow

1. The frontend submits a claim with `title`, optional `content`, and optional `source`.
2. The backend extracts heuristic feature signals from the request.
3. The backend invokes the classical Python scorer.
4. The backend invokes the FastAPI DistilBERT service.
5. The backend applies hybrid scoring logic and generates an explanation.
6. The backend stores the result through EF Core.
7. The frontend renders the final risk assessment and explainability fields.

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | React 18, Vite, React Router |
| Backend API | ASP.NET Core Web API, .NET 8 |
| Persistence | EF Core, Azure SQL or InMemory provider |
| Classical ML | Python, scikit-learn, TF-IDF, Logistic Regression, Random Forest |
| Transformer Service | FastAPI, HuggingFace Transformers, PyTorch |
| Dataset | LIAR |
| Tooling | npm, pip, PowerShell / Bash scripts |

## Repository Structure

```text
backend/
  Controllers/
  Data/
  Models/
  Services/
    Ml/
      artifacts/
      classical_predict.py
      train_classical_models.py

frontend/
  src/
    components/
    pages/

bert_service/
  main.py
  train.py
  models/

scripts/
  setup_liar_dataset.py
  train_all.sh
  train_all.ps1
  dev_start.sh
  dev_start.ps1

data/
  liar/
```

## Local Development Setup

### Prerequisites

- .NET 8 SDK
- Node.js 20+ and npm 10+
- Python 3.10+ for the ML pipeline
- Internet access for first-time dependency installation and optional model/dataset download

### Recommended Versions

- Windows: official CPython 3.11 x64
- macOS/Linux: Python 3.11 or 3.12
- Node.js: 20+ or 22+

### First-Time Setup

Copy the environment template:

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

## Environment Variables

The project reads configuration from `.env` and standard ASP.NET / Vite environment binding.

| Variable | Purpose | Example |
| --- | --- | --- |
| `ASPNETCORE_ENVIRONMENT` | Backend environment | `Development` |
| `ASPNETCORE_URLS` | Backend bind URL | `http://localhost:5000` |
| `ConnectionStrings__DefaultConnection` | Azure SQL connection string | empty for local in-memory mode |
| `PYTHON_BIN` | Python executable for setup scripts | `python` or absolute path |
| `MachineLearning__PythonExecutable` | Python executable used by backend scoring | absolute path to `.venv` or system Python |
| `MachineLearning__ClassicalPredictScriptPath` | Backend classical scorer entry point | `Services/Ml/classical_predict.py` |
| `MachineLearning__ClassicalModelDirectory` | Classical artifact folder | `Services/Ml/artifacts` |
| `BertService__Url` | Backend URL for the FastAPI service | `http://localhost:8001` |
| `VITE_API_BASE_URL` | Frontend API base URL | `http://localhost:5000` |
| `BERT_SETUP_MODE` | DistilBERT setup mode | `pretrained` or `train` |
| `BERT_MODEL_DIR` | Local model directory used by `bert_service` | `./bert_service/models/distilbert-liar` |
| `BERT_MODEL_NAME` | Optional explicit HuggingFace model override | empty by default |
| `BERT_MAX_LENGTH` | Token truncation length | `256` |

## Run Instructions

### Option A: One-Command Local Setup

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

### Option B: Run Each Service Manually

#### 1. Prepare Python and frontend dependencies

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

#### 2. Prepare the LIAR dataset

Windows PowerShell:

```powershell
& .\.venv\Scripts\python.exe .\scripts\setup_liar_dataset.py --output-dir .\data\liar
```

macOS/Linux:

```bash
python scripts/setup_liar_dataset.py --output-dir ./data/liar
```

#### 3. Train classical ML artifacts

Windows PowerShell:

```powershell
& .\.venv\Scripts\python.exe .\backend\Services\Ml\train_classical_models.py `
  --dataset-root .\data\liar `
  --output-dir .\backend\Services\Ml\artifacts
```

macOS/Linux:

```bash
python backend/Services/Ml/train_classical_models.py \
  --dataset-root ./data/liar \
  --output-dir ./backend/Services/Ml/artifacts
```

#### 4. Prepare a local DistilBERT checkpoint

Windows PowerShell:

```powershell
& .\.venv\Scripts\python.exe .\bert_service\train.py `
  --mode pretrained `
  --output-dir .\bert_service\models\distilbert-liar
```

macOS/Linux:

```bash
python bert_service/train.py \
  --mode pretrained \
  --output-dir ./bert_service/models/distilbert-liar
```

#### 5. Start `bert_service` in a new terminal

Windows PowerShell:

```powershell
Set-Location .\bert_service
& ..\.venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8001
```

macOS/Linux:

```bash
cd bert_service
../.venv/bin/python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

#### 6. Start backend in a new terminal from the repository root

Windows PowerShell:

```powershell
$env:BertService__Url = "http://localhost:8001"
$env:ASPNETCORE_URLS = "http://localhost:5000"
dotnet run --project .\backend\MisinformationRiskAssessment.Api.csproj
```

macOS/Linux:

```bash
export BertService__Url=http://localhost:8001
export ASPNETCORE_URLS=http://localhost:5000
dotnet run --project ./backend/MisinformationRiskAssessment.Api.csproj
```

#### 7. Start frontend in a new terminal from the repository root

Windows PowerShell:

```powershell
$env:VITE_API_BASE_URL = "http://localhost:5000"
npm.cmd --prefix .\frontend run dev:host
```

macOS/Linux:

```bash
export VITE_API_BASE_URL=http://localhost:5000
npm --prefix ./frontend run dev:host
```

### Default Local URLs

- Frontend: `http://localhost:5173/analyzer`
- Backend API: `http://localhost:5000`
- Swagger UI: `http://localhost:5000/swagger`
- BERT Service: `http://localhost:8001/health`

## Docker

The repository includes Docker support as an additional runtime option. It does not replace the existing local development scripts.

### Services Included

- `frontend`
- `backend`
- `bert_service`

### Start the Full Stack

```bash
docker compose up --build
```

### Stop the Stack

```bash
docker compose down
```

To stop the stack and remove anonymous volumes:

```bash
docker compose down -v
```

### Port Mapping

| Service | Container Port | Host Port |
| --- | --- | --- |
| Frontend | `80` | `5173` |
| Backend | `5000` | `5000` |
| BERT Service | `8001` | `8001` |

### Docker Runtime Notes

- The backend talks to the transformer container through `http://bert_service:8001`.
- The frontend is served by nginx and proxies `/api/*` to the backend container.
- Classical ML artifacts are mounted into the backend container from `backend/Services/Ml/artifacts`.
- Transformer model files are mounted into the BERT container from `bert_service/models`.
- Backend logs can be mounted through the `logs/` directory.

### Required Local Files Before `docker compose up`

At minimum, make sure these directories exist:

```text
backend/Services/Ml/artifacts/
bert_service/models/
logs/
```

If classical artifacts are missing, the backend startup validation will fail.

### Common Docker Commands

Rebuild after Dockerfile or dependency changes:

```bash
docker compose up --build
```

Run in detached mode:

```bash
docker compose up --build -d
```

Inspect service logs:

```bash
docker compose logs -f backend
docker compose logs -f bert_service
docker compose logs -f frontend
```

### Common Docker Issues

#### Backend fails startup validation

Typical causes:

- `backend/Services/Ml/artifacts` does not contain the trained `.joblib` files
- `bert_service` is not healthy yet
- `MachineLearning__PythonExecutable` was overridden incorrectly

#### Frontend loads but cannot call the API

Check:

- `frontend` is up
- `backend` healthcheck passes
- nginx is proxying `/api` correctly
- the backend is listening on `http://+:5000`

#### BERT service cannot load a model

Check:

- `bert_service/models/distilbert-liar` contains a valid local checkpoint
- or allow the container to download the fallback HuggingFace model on first startup

#### Docker build is using stale frontend configuration

`VITE_API_BASE_URL` is injected at image build time. Rebuild the frontend image after changes:

```bash
docker compose up --build frontend
```

## API Endpoints

| Method | Route | Description |
| --- | --- | --- |
| `GET` | `/api/health` | Returns backend health plus dependency checks |
| `POST` | `/api/analyze` | Runs the hybrid misinformation assessment pipeline |
| `GET` | `/api/history` | Returns recent analysis history |
| `GET` | `/api/result/{id}` | Returns a stored analysis record |

## Example Request / Response

### Input Contract

The project accepts the following request fields:

- `title`
- `content`
- `source`

### Output Contract

The project returns the following top-level fields:

- `riskLevel`
- `confidenceScore`
- `explanation`
- `featureSignals`

### `GET /api/health`

```bash
curl http://localhost:5000/api/health
```

Sample response:

```json
{
  "status": "Healthy",
  "timestamp": "2026-03-21T09:14:22Z",
  "checks": {
    "database": "in-memory",
    "bertService": "healthy",
    "classicalScript": "healthy",
    "classicalArtifacts": "available"
  }
}
```

### `POST /api/analyze`

```bash
curl -X POST http://localhost:5000/api/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "title": "The COVID-19 vaccine contains microchips for tracking",
    "content": "A viral post claims governments embedded tracking chips in vaccines.",
    "source": ""
  }'
```

Sample response:

```json
{
  "id": "6fa8ce9f-5e08-4ec8-bd4a-6d10db1b6d3f",
  "riskLevel": "Medium",
  "confidenceScore": 0.669,
  "explanation": "The claim is assessed as medium risk with a weighted misinformation score of 0.67. It lacks a named source, contains exaggeration cues, offers limited context. Key lexical signals include microchips, tracking, vaccine. The transformer model focused on covid, vaccine, microchips.",
  "featureSignals": {
    "textLength": 116,
    "wordCount": 17,
    "punctuationCount": 1,
    "emotionalWordRatio": 0.0,
    "uppercaseRatio": 0.0,
    "exclamationCount": 0,
    "exaggerationCount": 1,
    "hasSource": false,
    "topKeywords": [
      "microchips",
      "tracking",
      "vaccine"
    ],
    "transformerTokens": [
      "covid",
      "vaccine",
      "microchips"
    ],
    "modelScores": {
      "logisticRegression": 0.58,
      "randomForest": 0.54,
      "bert": 0.61,
      "hybrid": 0.669
    }
  },
  "createdAt": "2026-03-21T09:15:02Z"
}
```

## Hybrid Scoring Logic

The base ensemble score is computed as:

```text
0.5 * Logistic Regression
+ 0.3 * Random Forest
+ 0.2 * DistilBERT
```

In other words:

```text
hybrid_base_score
= 0.5 * logisticScore
+ 0.3 * randomForestScore
+ 0.2 * bertScore
```

After that weighted blend, the backend applies small rule-based adjustments to reflect interpretable surface cues such as:

- missing source
- elevated emotional wording
- excessive uppercase usage
- repeated exclamation marks
- exaggeration cues
- unusually short context
- trusted source patterns

The final score is clamped to `[0, 1]` and mapped to:

- `Low`
- `Medium`
- `High`

## Explainability Output

Each analysis returns explainability metadata through `featureSignals`.

The explainability payload includes:

- `feature signals`
- `top keywords`
- `transformer tokens`
- `model scores`

### Explainability Fields

- `featureSignals.textLength`
- `featureSignals.wordCount`
- `featureSignals.punctuationCount`
- `featureSignals.emotionalWordRatio`
- `featureSignals.uppercaseRatio`
- `featureSignals.exclamationCount`
- `featureSignals.exaggerationCount`
- `featureSignals.hasSource`
- `featureSignals.topKeywords`
- `featureSignals.transformerTokens`
- `featureSignals.modelScores`

### What They Mean

- `feature signals`: handcrafted heuristics extracted directly from the request text
- `top keywords`: the most influential lexical terms coming from the classical ML pipeline
- `transformer tokens`: salient tokens surfaced by the DistilBERT service
- `model scores`: per-model contribution snapshot for Logistic Regression, Random Forest, BERT, and final hybrid output

## Demo Walkthrough

### Example Claim

`The COVID-19 vaccine contains microchips for tracking`

### Expected Result Type

A representative output for this example is `Medium` risk.

### Why Medium Risk

This claim tends to sit in the medium-risk range because it activates several suspicious signals without necessarily maxing out every high-risk heuristic:

- the claim is short and offers limited context
- it does not provide a named source
- it contains conspiracy-style lexical cues such as `microchips` and `tracking`
- classical models usually react to those terms strongly
- the transformer service identifies semantically salient tokens around vaccine misinformation themes

### Triggered Explainability Signals

Typical triggered signals for this example include:

- `hasSource = false`
- low contextual depth due to short input length
- `topKeywords` including `microchips`, `tracking`, and `vaccine`
- `transformerTokens` including `covid`, `vaccine`, and `microchips`
- nontrivial scores across all three model branches, resulting in a medium-risk ensemble outcome

## Benchmark

The repository includes evaluation outputs for:

- Logistic Regression
- Random Forest
- DistilBERT
- Hybrid Model

### Evaluation Protocol

The benchmark follows the LIAR file split directly:

- `train.tsv` for model fitting
- `valid.tsv` for validation reporting
- `test.tsv` for final comparison

The benchmark entrypoint is:

Windows PowerShell:

```powershell
.\scripts\run_benchmark.ps1
```

macOS/Linux:

```bash
./scripts/run_benchmark.sh
```

Generated outputs:

- `reports/benchmark.json`
- `reports/benchmark.md`
- `reports/benchmark.csv`

### Label Mapping

The project uses a binary mapping over the original LIAR labels:

| Original Label | Benchmark Label |
| --- | --- |
| `true` | `0` |
| `mostly-true` | `0` |
| `half-true` | `0` |
| `barely-true` | `1` |
| `false` | `1` |
| `pants-fire` | `1` |

Interpretation:

- `0` means lower misinformation risk
- `1` means higher misinformation risk

### Metrics Reported

All benchmark outputs include:

- Accuracy
- Precision
- Recall
- F1
- ROC AUC where score-based evaluation applies

### Model Comparison Table

The benchmark script writes a Markdown-ready table to `reports/benchmark.md`.

Example layout:

| Model | Accuracy | Precision | Recall | F1 | ROC AUC |
| --- | ---: | ---: | ---: | ---: | ---: |
| Logistic Regression | 0.7420 | 0.7310 | 0.7680 | 0.7490 | 0.8110 |
| Random Forest | 0.7180 | 0.7020 | 0.7540 | 0.7270 | 0.7840 |
| DistilBERT | 0.7560 | 0.7490 | 0.7710 | 0.7600 | 0.8260 |
| Hybrid | 0.7810 | 0.7740 | 0.7980 | 0.7860 | 0.8470 |

### Hybrid Model Value

The hybrid model is useful when it improves balance rather than just one metric in isolation.

In this project, the hybrid layer combines:

- lexical signals from Logistic Regression
- nonlinear feature interactions from Random Forest
- semantic context from DistilBERT
- lightweight rule-based calibration from the backend scoring layer

The benchmark outputs are intended to show whether that combination produces a more stable test-set tradeoff than any single model alone. If the hybrid result only improves one metric while degrading others, the report should be read conservatively.

## Troubleshooting

### `dotnet` cannot find an SDK

- Install the .NET 8 SDK, not just the runtime.
- Verify with:

```bash
dotnet --list-sdks
```

### Frontend dependencies are missing

Windows PowerShell:

```powershell
npm.cmd --prefix .\frontend install
```

macOS/Linux:

```bash
npm --prefix ./frontend install
```

### Backend startup validation fails

Check these items:

- `MachineLearning__PythonExecutable` points to a valid interpreter
- `backend/Services/Ml/classical_predict.py` exists
- classical artifact files exist under `backend/Services/Ml/artifacts`
- `BertService__Url` points to the running FastAPI service

### LIAR dataset download fails

Use the manual fallback:

```bash
python scripts/setup_liar_dataset.py --zip-file /path/to/liar_dataset.zip
```

Then confirm:

```text
data/liar/train.tsv
data/liar/valid.tsv
data/liar/test.tsv
```

### HuggingFace model download fails

Point the service to a prepared local model directory:

Windows PowerShell:

```powershell
$env:BERT_MODEL_DIR = "C:\path\to\local\model"
```

macOS/Linux:

```bash
export BERT_MODEL_DIR=/absolute/path/to/local/model
```

### PowerShell blocks `npm`

Use `npm.cmd` instead of `npm`, or use the provided PowerShell scripts.

## Future Improvements

- Replace heuristic score adjustments with calibrated post-processing
- Fine-tune DistilBERT directly on a larger misinformation-focused corpus
- Add confidence calibration and threshold evaluation dashboards
- Extend explainability with SHAP or per-feature attribution views
- Add CI pipelines for backend, frontend, and ML artifact validation
- Add Docker Compose for fully reproducible local startup
- Support batch inference and asynchronous job processing
- Add authentication and multi-user result history

## Additional Documentation

For a deeper architecture-oriented write-up, see [docs/ARCHITECTURE.md](C:/Users/Administrator/Desktop/MLops/docs/ARCHITECTURE.md).
