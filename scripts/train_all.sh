#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

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
BERT_OUTPUT_DIR="${BERT_OUTPUT_DIR:-$ROOT_DIR/bert_service/models/distilbert-liar}"
BERT_SETUP_MODE="${BERT_SETUP_MODE:-pretrained}"
TMPDIR="${TMPDIR:-$ROOT_DIR/.tmp}"
PIP_CACHE_DIR="${PIP_CACHE_DIR:-$ROOT_DIR/.pip-cache}"
npm_config_cache="${npm_config_cache:-$ROOT_DIR/.npm-cache}"

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

require_command "$PYTHON_BIN"
require_command npm

if [[ ! -d "$VENV_DIR" ]]; then
  "$PYTHON_BIN" -m venv "$VENV_DIR"
fi

if [[ -x "$VENV_DIR/bin/python" ]] && "$VENV_DIR/bin/python" -m pip --version >/dev/null 2>&1; then
  PYTHON_BIN="$VENV_DIR/bin/python"
elif [[ -x "$VENV_DIR/bin/python" ]]; then
  echo "Warning: virtual environment exists but pip is unavailable. Falling back to $PYTHON_BIN."
fi

"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install -r backend/Services/Ml/requirements.txt
"$PYTHON_BIN" -m pip install -r bert_service/requirements.txt

npm --prefix frontend install

"$PYTHON_BIN" scripts/setup_liar_dataset.py --output-dir "$DATASET_ROOT"

"$PYTHON_BIN" backend/Services/Ml/train_classical_models.py \
  --dataset-root "$DATASET_ROOT" \
  --output-dir "$CLASSICAL_ARTIFACT_DIR"

"$PYTHON_BIN" bert_service/train.py \
  --mode "$BERT_SETUP_MODE" \
  --dataset-root "$DATASET_ROOT" \
  --output-dir "$BERT_OUTPUT_DIR"

echo
echo "Training setup complete."
echo "Classical artifacts: $CLASSICAL_ARTIFACT_DIR"
echo "BERT model directory: $BERT_OUTPUT_DIR"
echo "Next step: ./scripts/dev_start.sh"
