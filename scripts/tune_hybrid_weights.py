#!/usr/bin/env python3
"""Tune the hybrid ensemble weights on the LIAR validation split.

This script only ever loads valid.tsv. The test split is not read here, so the
selection cannot be contaminated by it; run scripts/evaluate_hybrid.py once,
afterwards, to obtain the reported test numbers.

The chosen weights are written to reports/hybrid_weights.json as an auditable
record. Apply them to backend/appsettings.json under MachineLearning:HybridWeights
- that file is the single source of truth read by both the .NET scoring service
and the benchmark, so the benchmark can never report weights production is not
using.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

import joblib
import numpy as np
import torch
from scipy.sparse import csr_matrix, hstack
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer

REPO_ROOT = Path(__file__).resolve().parents[1]
ML_DIR = REPO_ROOT / "backend" / "Services" / "Ml"
BERT_DIR = REPO_ROOT / "bert_service"
for extra_path in (ML_DIR, BERT_DIR):
    if str(extra_path) not in sys.path:
        sys.path.insert(0, str(extra_path))

from common import extract_rule_features, feature_matrix, load_liar_records  # noqa: E402
from data_utils import load_liar as load_liar_for_bert  # noqa: E402
from evaluate_hybrid import (  # noqa: E402
    hybrid_adjustment,
    verify_bert_checkpoint,
    verify_classical_artifacts,
)

TUNING_SPLIT = "valid"


def score_components(records, bert_records, artifact_dir: Path, bert_model_dir: Path, batch_size: int, max_length: int):
    texts = [str(record["text"]) for record in records]
    numeric_rows = feature_matrix(records)

    vectorizer = joblib.load(artifact_dir / "tfidf_vectorizer.joblib")
    logistic = joblib.load(artifact_dir / "logistic_regression.joblib")
    random_forest = joblib.load(artifact_dir / "random_forest.joblib")

    features = hstack(
        [vectorizer.transform(texts), csr_matrix(np.asarray(numeric_rows, dtype=np.float64))]
    ).tocsr()

    tokenizer = AutoTokenizer.from_pretrained(str(bert_model_dir))
    model = AutoModelForSequenceClassification.from_pretrained(str(bert_model_dir))
    model.eval()

    bert_texts = [str(record["text"]) for record in bert_records]
    bert_scores: list[float] = []
    with torch.no_grad():
        for start in range(0, len(bert_texts), batch_size):
            encoded = tokenizer(
                bert_texts[start : start + batch_size],
                truncation=True,
                padding=True,
                max_length=max_length,
                return_tensors="pt",
            )
            probabilities = torch.softmax(model(**encoded).logits, dim=-1)[:, 1]
            bert_scores.extend(float(value) for value in probabilities.cpu().tolist())

    return (
        logistic.predict_proba(features)[:, 1],
        random_forest.predict_proba(features)[:, 1],
        np.asarray(bert_scores, dtype=np.float64),
    )


def combine(weights, logistic_scores, random_forest_scores, bert_scores, adjustments) -> np.ndarray:
    weight_lr, weight_rf, weight_bert = weights
    weighted = weight_lr * logistic_scores + weight_rf * random_forest_scores + weight_bert * bert_scores
    return np.clip(weighted + adjustments, 0.0, 1.0)


def summarize(labels: np.ndarray, scores: np.ndarray, threshold: float) -> dict[str, float]:
    predictions = (scores >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average="binary", zero_division=0
    )
    return {
        "accuracy": round(float(accuracy_score(labels, predictions)), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "roc_auc": round(float(roc_auc_score(labels, scores)), 4),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Tune hybrid ensemble weights on the LIAR validation split.")
    parser.add_argument("--dataset-root", default=str(REPO_ROOT / "data" / "liar"))
    parser.add_argument("--classical-artifact-dir", default=str(ML_DIR / "artifacts"))
    parser.add_argument("--bert-model-dir", default=str(BERT_DIR / "models" / "distilbert-liar"))
    parser.add_argument("--report-dir", default=str(REPO_ROOT / "reports"))
    parser.add_argument("--score-threshold", type=float, default=0.5)
    parser.add_argument("--step", type=float, default=0.05, help="Grid resolution over the weight simplex.")
    parser.add_argument("--bert-batch-size", type=int, default=32)
    parser.add_argument("--bert-max-length", type=int, default=256)
    parser.add_argument(
        "--criterion",
        choices=["roc_auc", "f1", "accuracy"],
        default="roc_auc",
        help="Validation metric maximised by the grid search. ROC AUC is threshold-free and the most stable.",
    )
    args = parser.parse_args()

    # Weights tuned against stale artifacts would be applied to different models.
    verify_classical_artifacts(Path(args.classical_artifact_dir))
    verify_bert_checkpoint(Path(args.bert_model_dir), allow_placeholder=False)

    records = [r for r in load_liar_records(args.dataset_root) if str(r.get("split")) == TUNING_SPLIT]
    bert_records = [r for r in load_liar_for_bert(args.dataset_root) if str(r.get("split")) == TUNING_SPLIT]
    if not records:
        raise SystemExit(f"No LIAR {TUNING_SPLIT} records were found for weight tuning.")

    labels = np.asarray([int(r["label"]) for r in records], dtype=np.int64)
    if len(bert_records) != len(records) or [int(r["label"]) for r in bert_records] != labels.tolist():
        raise SystemExit(
            f"LIAR loaders disagree on the {TUNING_SPLIT} split: "
            f"classical={len(records)} rows, bert={len(bert_records)} rows. "
            "backend/Services/Ml/common.py and bert_service/data_utils.py must stay row-aligned."
        )

    logistic_scores, random_forest_scores, bert_scores = score_components(
        records,
        bert_records,
        Path(args.classical_artifact_dir),
        Path(args.bert_model_dir),
        args.bert_batch_size,
        args.bert_max_length,
    )

    adjustments = np.asarray(
        [
            hybrid_adjustment(
                record,
                extract_rule_features(
                    str(record.get("title") or ""),
                    str(record.get("content") or ""),
                    str(record.get("source") or ""),
                ),
            )
            for record in records
        ],
        dtype=np.float64,
    )

    steps = int(round(1.0 / args.step))
    candidates = []
    for lr_units, rf_units in product(range(steps + 1), repeat=2):
        bert_units = steps - lr_units - rf_units
        if bert_units < 0:
            continue
        weights = (lr_units / steps, rf_units / steps, bert_units / steps)
        scores = combine(weights, logistic_scores, random_forest_scores, bert_scores, adjustments)
        candidates.append((weights, summarize(labels, scores, args.score_threshold)))

    best_weights, best_metrics = max(candidates, key=lambda item: item[1][args.criterion])
    baseline_weights = (0.5, 0.3, 0.2)
    baseline_metrics = summarize(
        labels,
        combine(baseline_weights, logistic_scores, random_forest_scores, bert_scores, adjustments),
        args.score_threshold,
    )

    singles = {
        "logisticRegression": summarize(labels, logistic_scores, args.score_threshold),
        "randomForest": summarize(labels, random_forest_scores, args.score_threshold),
        "distilBert": summarize(labels, bert_scores, args.score_threshold),
    }

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "LIAR",
        "tuning_split": f"{TUNING_SPLIT}.tsv",
        "note": (
            "Weights selected on the validation split only. The test split is never read by "
            "this script; run scripts/evaluate_hybrid.py once afterwards for reported test metrics."
        ),
        "selection": {
            "criterion": args.criterion,
            "grid_step": args.step,
            "candidates_evaluated": len(candidates),
            "score_threshold": args.score_threshold,
        },
        "record_count": len(records),
        "weights": {
            "logisticRegression": round(best_weights[0], 4),
            "randomForest": round(best_weights[1], 4),
            "bert": round(best_weights[2], 4),
        },
        "validation_metrics": {
            "tuned_hybrid": best_metrics,
            "baseline_hybrid_0.5_0.3_0.2": baseline_metrics,
            "single_models": singles,
        },
        "apply_to": "backend/appsettings.json -> MachineLearning:HybridWeights",
    }

    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "hybrid_weights.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
