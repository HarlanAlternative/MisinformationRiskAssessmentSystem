#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

LOG_DIR="$ROOT_DIR/logs"
mkdir -p "$LOG_DIR"

if [[ -f ".env" ]]; then
  set -a
  source ".env"
  set +a
fi

detect_python() {
  if command -v python3 >/dev/null 2>&1; then
    echo "python3"
    return 0
  fi

  if command -v python >/dev/null 2>&1; then
    echo "python"
    return 0
  fi

  return 1
}

PYTHON_BIN="${PYTHON_BIN:-$(detect_python)}"
VENV_DIR="${VENV_DIR:-$ROOT_DIR/.venv}"
DATASET_ROOT="${DATASET_ROOT:-$ROOT_DIR/data/liar}"
CLASSICAL_ARTIFACT_DIR="${CLASSICAL_ARTIFACT_DIR:-$ROOT_DIR/backend/Services/Ml/artifacts}"
ASPNETCORE_URLS="${ASPNETCORE_URLS:-http://localhost:5000}"
BertService__Url="${BertService__Url:-http://localhost:8001}"
VITE_API_BASE_URL="${VITE_API_BASE_URL:-http://localhost:5000}"
TMPDIR="${TMPDIR:-$ROOT_DIR/.tmp}"
PIP_CACHE_DIR="${PIP_CACHE_DIR:-$ROOT_DIR/.pip-cache}"
npm_config_cache="${npm_config_cache:-$ROOT_DIR/.npm-cache}"

export ASPNETCORE_ENVIRONMENT="${ASPNETCORE_ENVIRONMENT:-Development}"
export ASPNETCORE_URLS
export BertService__Url
export VITE_API_BASE_URL
mkdir -p "$TMPDIR" "$PIP_CACHE_DIR" "$npm_config_cache"
export TMPDIR
export TEMP="$TMPDIR"
export TMP="$TMPDIR"
export PIP_CACHE_DIR
export npm_config_cache

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1"
    exit 1
  fi
}

require_file() {
  if [[ ! -f "$1" ]]; then
    echo "$2"
    exit 1
  fi
}

wait_for_url() {
  local url="$1"
  local name="$2"
  local attempts="${3:-40}"

  for ((i=1; i<=attempts; i++)); do
    if "$PYTHON_BIN" - "$url" <<'PY' >/dev/null 2>&1
import sys
import urllib.request

url = sys.argv[1]
with urllib.request.urlopen(url, timeout=2) as response:
    if response.status < 500:
        sys.exit(0)
sys.exit(1)
PY
    then
      echo "$name is ready at $url"
      return 0
    fi
    sleep 1
  done

  echo "Timed out waiting for $name at $url"
  return 1
}

require_command "$PYTHON_BIN"
require_command dotnet
require_command npm

if [[ -d "$VENV_DIR" ]]; then
  if [[ -x "$VENV_DIR/bin/python" ]] && "$VENV_DIR/bin/python" -m pip --version >/dev/null 2>&1; then
    PYTHON_BIN="$VENV_DIR/bin/python"
  elif [[ -x "$VENV_DIR/Scripts/python.exe" ]]; then
    PYTHON_BIN="$VENV_DIR/Scripts/python.exe"
  fi
fi

export MachineLearning__PythonExecutable="${MachineLearning__PythonExecutable:-$PYTHON_BIN}"

if [[ ! -d "frontend/node_modules" ]]; then
  echo "Frontend dependencies are missing. Run ./scripts/train_all.sh first."
  exit 1
fi

require_file "$DATASET_ROOT/train.tsv" "LIAR dataset is missing. Run ./scripts/setup_liar_dataset.py first."
require_file "$DATASET_ROOT/valid.tsv" "LIAR dataset is incomplete. Expected valid.tsv under $DATASET_ROOT."
require_file "$DATASET_ROOT/test.tsv" "LIAR dataset is incomplete. Expected test.tsv under $DATASET_ROOT."
require_file "$CLASSICAL_ARTIFACT_DIR/tfidf_vectorizer.joblib" "Classical artifacts are missing. Run ./scripts/train_all.sh first."
require_file "$CLASSICAL_ARTIFACT_DIR/logistic_regression.joblib" "Classical artifacts are missing. Run ./scripts/train_all.sh first."
require_file "$CLASSICAL_ARTIFACT_DIR/random_forest.joblib" "Classical artifacts are missing. Run ./scripts/train_all.sh first."

BERT_PID=""
BACKEND_PID=""

cleanup() {
  if [[ -n "$BACKEND_PID" ]] && kill -0 "$BACKEND_PID" >/dev/null 2>&1; then
    kill "$BACKEND_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "$BERT_PID" ]] && kill -0 "$BERT_PID" >/dev/null 2>&1; then
    kill "$BERT_PID" >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT INT TERM

echo "Starting bert_service..."
(
  cd "$ROOT_DIR/bert_service"
  exec "$PYTHON_BIN" -m uvicorn main:app --host 0.0.0.0 --port 8001
) >"$LOG_DIR/bert_service.log" 2>&1 &
BERT_PID=$!

wait_for_url "http://127.0.0.1:8001/health" "bert_service"

echo "Starting backend..."
(
  cd "$ROOT_DIR"
  exec dotnet run --project backend/MisinformationRiskAssessment.Api.csproj
) >"$LOG_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

wait_for_url "http://127.0.0.1:5000/api/health" "backend API"

echo "Starting frontend..."
echo "Logs:"
echo "  bert_service: $LOG_DIR/bert_service.log"
echo "  backend:      $LOG_DIR/backend.log"
echo "Frontend will run in the current terminal. Press Ctrl+C to stop all services."

cd "$ROOT_DIR/frontend"
exec npm run dev:host
