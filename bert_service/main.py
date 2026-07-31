from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from transformers import AutoModelForSequenceClassification, AutoTokenizer


class PredictRequest(BaseModel):
    title: str = Field(..., min_length=1)
    content: str | None = None
    source: str | None = None


class PredictResponse(BaseModel):
    score: float
    label: str
    salientTokens: list[str]


class State:
    tokenizer = None
    model = None
    device = torch.device("cpu")
    max_length = 256
    model_reference = ""
    model_source = ""


state = State()


def env_flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def describe_checkpoint(model_dir: Path) -> str:
    """Report whether a local checkpoint is a LIAR fine-tune or the SST-2 placeholder."""
    info_path = model_dir / "model_info.json"
    if not info_path.exists():
        return "local"

    try:
        mode = json.loads(info_path.read_text(encoding="utf-8")).get("mode")
    except (OSError, ValueError):
        return "local"

    return "placeholder" if mode == "pretrained" else "local"


def choose_model_reference() -> str:
    """Resolve the checkpoint to serve, refusing to quietly substitute a wrong one.

    This used to fall back to a sentiment model when no checkpoint was present,
    which meant a deployment with an empty model directory came up healthy and
    served scores from a model that has nothing to do with misinformation. An
    absent checkpoint is now a startup failure.
    """
    default_local_dir = Path(__file__).resolve().parent / "models" / "distilbert-liar"
    configured_dir = Path(os.getenv("BERT_MODEL_DIR", str(default_local_dir)))
    configured_name = os.getenv("BERT_MODEL_NAME")

    if configured_dir.exists() and (configured_dir / "config.json").exists():
        state.model_source = describe_checkpoint(configured_dir)
        if state.model_source == "placeholder":
            print(
                f"WARNING: '{configured_dir}' holds the SST-2 startup placeholder, not a LIAR "
                "fine-tune. Scores from it are meaningless for this task. Build the checkpoint "
                "with 'python train.py --mode train'.",
                flush=True,
            )
        return str(configured_dir)

    if configured_name:
        state.model_source = "configured"
        return configured_name

    if env_flag("BERT_ALLOW_PLACEHOLDER_FALLBACK"):
        state.model_source = "placeholder-fallback"
        fallback_name = os.getenv("BERT_FALLBACK_MODEL_NAME", "distilbert-base-uncased-finetuned-sst-2-english")
        print(
            f"WARNING: no checkpoint at '{configured_dir}'. Falling back to '{fallback_name}', a "
            "sentiment model unrelated to this task, because BERT_ALLOW_PLACEHOLDER_FALLBACK is set.",
            flush=True,
        )
        return fallback_name

    raise RuntimeError(
        f"No DistilBERT checkpoint found at '{configured_dir}'. The service will not start with a "
        "substitute model, because serving one silently reports misinformation scores from a model "
        "that never learned the task. Provide the fine-tuned checkpoint (see scripts/package_artifacts.py "
        "and the container build), set BERT_MODEL_NAME to a specific model, or set "
        "BERT_ALLOW_PLACEHOLDER_FALLBACK=true to accept the SST-2 placeholder deliberately."
    )


def compose_text(title: str, content: str | None, source: str | None) -> str:
    segments = [title.strip(), (content or "").strip(), (source or "").strip()]
    return " [SEP] ".join(segment for segment in segments if segment)


def decode_salient_tokens(input_ids: torch.Tensor, attentions) -> list[str]:
    if not attentions:
        return []

    attention_map = attentions[-1][0].mean(dim=0)[0]
    ranked_indices = torch.argsort(attention_map, descending=True).tolist()
    tokens = []
    seen = set()

    for index in ranked_indices:
        token = state.tokenizer.convert_ids_to_tokens(int(input_ids[0][index]))
        if token in {"[CLS]", "[SEP]", "[PAD]"}:
            continue
        token = token.replace("##", "")
        if len(token) < 3 or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
        if len(tokens) == 5:
            break

    return tokens


@asynccontextmanager
async def lifespan(_: FastAPI):
    model_reference = choose_model_reference()
    state.max_length = int(os.getenv("BERT_MAX_LENGTH", "256"))
    state.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    state.model_reference = model_reference

    try:
        state.tokenizer = AutoTokenizer.from_pretrained(model_reference)
        state.model = AutoModelForSequenceClassification.from_pretrained(model_reference)
    except Exception as exc:
        raise RuntimeError(
            "Failed to load the BERT model. "
            f"Tried '{model_reference}'. "
            "Set BERT_MODEL_DIR to a valid local checkpoint, or set BERT_MODEL_NAME/BERT_FALLBACK_MODEL_NAME to a downloadable HuggingFace model."
        ) from exc

    state.model.to(state.device)
    state.model.eval()
    yield


app = FastAPI(title="DistilBERT Misinformation Service", version="1.0.0", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "model": str(Path(state.model_reference).name if state.model_reference and Path(state.model_reference).exists() else state.model_reference),
        "modelSource": state.model_source,
    }


@app.post("/predict", response_model=PredictResponse)
async def predict(request: PredictRequest) -> PredictResponse:
    if state.model is None or state.tokenizer is None:
        raise HTTPException(status_code=503, detail="Model is not loaded.")

    text = compose_text(request.title, request.content, request.source)
    encoded = state.tokenizer(
        text,
        truncation=True,
        padding=True,
        max_length=state.max_length,
        return_tensors="pt",
    )
    encoded = {key: value.to(state.device) for key, value in encoded.items()}

    with torch.no_grad():
        outputs = state.model(**encoded, output_attentions=True)
        probabilities = torch.softmax(outputs.logits, dim=-1)[0]
        score = float(probabilities[1].item())
        salient = decode_salient_tokens(encoded["input_ids"].cpu(), outputs.attentions)

    label = "high_risk" if score >= 0.7 else "medium_risk" if score >= 0.35 else "low_risk"
    return PredictResponse(score=round(score, 4), label=label, salientTokens=salient)
