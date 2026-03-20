from __future__ import annotations

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


def choose_model_reference() -> str:
    default_local_dir = Path(__file__).resolve().parent / "models" / "distilbert-liar"
    configured_dir = Path(os.getenv("BERT_MODEL_DIR", str(default_local_dir)))
    configured_name = os.getenv("BERT_MODEL_NAME")
    fallback_name = os.getenv("BERT_FALLBACK_MODEL_NAME", "distilbert-base-uncased-finetuned-sst-2-english")

    if configured_dir.exists() and (configured_dir / "config.json").exists():
        state.model_source = "local"
        return str(configured_dir)

    if configured_name:
        state.model_source = "configured"
        return configured_name

    state.model_source = "fallback"
    return fallback_name


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
