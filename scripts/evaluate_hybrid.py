#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import torch
from scipy.sparse import csr_matrix, hstack
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score
from transformers import AutoModelForSequenceClassification, AutoTokenizer

REPO_ROOT = Path(__file__).resolve().parents[1]
ML_DIR = REPO_ROOT / "backend" / "Services" / "Ml"
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from common import extract_rule_features, feature_matrix, load_liar_records  # noqa: E402

DEFAULT_DATASET_ROOT = REPO_ROOT / "data" / "liar"
DEFAULT_CLASSICAL_ARTIFACT_DIR = REPO_ROOT / "backend" / "Services" / "Ml" / "artifacts"
DEFAULT_BERT_MODEL_DIR = REPO_ROOT / "bert_service" / "models" / "distilbert-liar"
DEFAULT_REPORT_DIR = REPO_ROOT / "reports"

TRUSTED_SOURCES = {"ap", "associated press", "bbc", "ft", "guardian", "nytimes", "reuters", "wsj"}


def build_sparse_matrix(vectorizer, texts: list[str], numeric_rows: list[list[float]]):
    tfidf = vectorizer.transform(texts)
    numeric = csr_matrix(np.asarray(numeric_rows, dtype=np.float64))
    return hstack([tfidf, numeric]).tocsr()


def compute_binary_metrics(y_true: np.ndarray, scores: np.ndarray, threshold: float = 0.5) -> dict[str, float | None]:
    predictions = (scores >= threshold).astype(int)
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        predictions,
        average="binary",
        zero_division=0,
    )

    metrics: dict[str, float | None] = {
        "accuracy": round(float(accuracy_score(y_true, predictions)), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
        "threshold": round(float(threshold), 4),
    }

    if len(np.unique(y_true)) > 1:
        metrics["roc_auc"] = round(float(roc_auc_score(y_true, scores)), 4)
    else:
        metrics["roc_auc"] = None

    return metrics


def looks_trusted(source: str | None) -> bool:
    if not source:
        return False
    return any(candidate in source.lower() for candidate in TRUSTED_SOURCES)


def hybrid_adjustment(record: dict[str, object], score_features: dict[str, float]) -> float:
    adjustment = 0.0

    if score_features["has_source"] < 0.5:
        adjustment += 0.05
    if score_features["emotional_word_ratio"] >= 0.03:
        adjustment += 0.04
    if score_features["uppercase_ratio"] >= 0.12:
        adjustment += 0.03
    if score_features["exclamation_count"] >= 2:
        adjustment += 0.03
    if score_features["exaggeration_count"] > 0:
        adjustment += min(0.05, score_features["exaggeration_count"] * 0.015)
    if score_features["word_count"] < 35:
        adjustment += 0.03
    if score_features["has_source"] >= 0.5 and looks_trusted(str(record.get("source") or "")):
        adjustment -= 0.03

    return adjustment


def write_csv(report_dir: Path, comparison_rows: list[dict[str, float | str | None]]) -> None:
    output_path = report_dir / "benchmark.csv"
    fieldnames = ["Model", "Accuracy", "Precision", "Recall", "F1", "ROC_AUC"]

    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in comparison_rows:
            writer.writerow(row)


def write_markdown(report_dir: Path, comparison_rows: list[dict[str, float | str | None]]) -> None:
    output_path = report_dir / "benchmark.md"
    lines = [
        "| Model | Accuracy | Precision | Recall | F1 | ROC AUC |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]

    for row in comparison_rows:
        roc_auc = row["ROC_AUC"]
        lines.append(
            f"| {row['Model']} | {row['Accuracy']:.4f} | {row['Precision']:.4f} | {row['Recall']:.4f} | {row['F1']:.4f} | {roc_auc:.4f} |"
            if isinstance(roc_auc, float)
            else f"| {row['Model']} | {row['Accuracy']:.4f} | {row['Precision']:.4f} | {row['Recall']:.4f} | {row['F1']:.4f} | n/a |"
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark classical, BERT, and hybrid models on LIAR test split.")
    parser.add_argument("--dataset-root", default=str(DEFAULT_DATASET_ROOT))
    parser.add_argument("--classical-artifact-dir", default=str(DEFAULT_CLASSICAL_ARTIFACT_DIR))
    parser.add_argument("--bert-model-dir", default=str(DEFAULT_BERT_MODEL_DIR))
    parser.add_argument("--report-dir", default=str(DEFAULT_REPORT_DIR))
    parser.add_argument("--score-threshold", type=float, default=0.5)
    parser.add_argument("--medium-risk-threshold", type=float, default=0.35)
    parser.add_argument("--high-risk-threshold", type=float, default=0.70)
    parser.add_argument("--bert-batch-size", type=int, default=16)
    parser.add_argument("--bert-max-length", type=int, default=256)
    args = parser.parse_args()

    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)

    records = [record for record in load_liar_records(args.dataset_root) if str(record.get("split")) == "test"]
    if not records:
        raise SystemExit("No LIAR test records were found for benchmark evaluation.")

    labels = np.asarray([int(record["label"]) for record in records], dtype=np.int64)
    texts = [str(record["text"]) for record in records]
    numeric_rows = feature_matrix(records)

    artifact_dir = Path(args.classical_artifact_dir)
    vectorizer = joblib.load(artifact_dir / "tfidf_vectorizer.joblib")
    logistic = joblib.load(artifact_dir / "logistic_regression.joblib")
    random_forest = joblib.load(artifact_dir / "random_forest.joblib")

    classical_features = build_sparse_matrix(vectorizer, texts, numeric_rows)
    logistic_scores = logistic.predict_proba(classical_features)[:, 1]
    random_forest_scores = random_forest.predict_proba(classical_features)[:, 1]

    bert_model_dir = Path(args.bert_model_dir)
    tokenizer = AutoTokenizer.from_pretrained(str(bert_model_dir))
    bert_model = AutoModelForSequenceClassification.from_pretrained(str(bert_model_dir))
    bert_model.eval()

    bert_scores_list: list[float] = []
    with torch.no_grad():
        for start in range(0, len(records), args.bert_batch_size):
            batch_records = records[start : start + args.bert_batch_size]
            encoded = tokenizer(
                [record["text"] for record in batch_records],
                truncation=True,
                padding=True,
                max_length=args.bert_max_length,
                return_tensors="pt",
            )
            outputs = bert_model(**encoded)
            probabilities = torch.softmax(outputs.logits, dim=-1)[:, 1]
            bert_scores_list.extend(float(score) for score in probabilities.cpu().tolist())

    bert_scores = np.asarray(bert_scores_list, dtype=np.float64)

    hybrid_scores_list: list[float] = []
    risk_level_counts = {"Low": 0, "Medium": 0, "High": 0}

    for index, record in enumerate(records):
        features = extract_rule_features(
            str(record.get("title") or ""),
            str(record.get("content") or ""),
            str(record.get("source") or ""),
        )
        weighted_score = (
            (0.5 * float(logistic_scores[index]))
            + (0.3 * float(random_forest_scores[index]))
            + (0.2 * float(bert_scores[index]))
        )
        final_score = min(1.0, max(0.0, weighted_score + hybrid_adjustment(record, features)))
        hybrid_scores_list.append(final_score)

        if final_score >= args.high_risk_threshold:
            risk_level_counts["High"] += 1
        elif final_score >= args.medium_risk_threshold:
            risk_level_counts["Medium"] += 1
        else:
            risk_level_counts["Low"] += 1

    hybrid_scores = np.asarray(hybrid_scores_list, dtype=np.float64)

    model_metrics = {
        "logisticRegression": compute_binary_metrics(labels, logistic_scores, args.score_threshold),
        "randomForest": compute_binary_metrics(labels, random_forest_scores, args.score_threshold),
        "distilBert": compute_binary_metrics(labels, bert_scores, args.score_threshold),
        "hybrid": compute_binary_metrics(labels, hybrid_scores, args.score_threshold),
    }

    comparison_rows = [
        {
            "Model": "Logistic Regression",
            "Accuracy": model_metrics["logisticRegression"]["accuracy"],
            "Precision": model_metrics["logisticRegression"]["precision"],
            "Recall": model_metrics["logisticRegression"]["recall"],
            "F1": model_metrics["logisticRegression"]["f1"],
            "ROC_AUC": model_metrics["logisticRegression"]["roc_auc"],
        },
        {
            "Model": "Random Forest",
            "Accuracy": model_metrics["randomForest"]["accuracy"],
            "Precision": model_metrics["randomForest"]["precision"],
            "Recall": model_metrics["randomForest"]["recall"],
            "F1": model_metrics["randomForest"]["f1"],
            "ROC_AUC": model_metrics["randomForest"]["roc_auc"],
        },
        {
            "Model": "DistilBERT",
            "Accuracy": model_metrics["distilBert"]["accuracy"],
            "Precision": model_metrics["distilBert"]["precision"],
            "Recall": model_metrics["distilBert"]["recall"],
            "F1": model_metrics["distilBert"]["f1"],
            "ROC_AUC": model_metrics["distilBert"]["roc_auc"],
        },
        {
            "Model": "Hybrid",
            "Accuracy": model_metrics["hybrid"]["accuracy"],
            "Precision": model_metrics["hybrid"]["precision"],
            "Recall": model_metrics["hybrid"]["recall"],
            "F1": model_metrics["hybrid"]["f1"],
            "ROC_AUC": model_metrics["hybrid"]["roc_auc"],
        },
    ]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "LIAR",
        "evaluation_protocol": {
            "train_split": "train.tsv",
            "validation_split": "valid.tsv",
            "test_split": "test.tsv",
            "benchmark_split": "test.tsv",
            "label_mapping": {
                "true": 0,
                "mostly-true": 0,
                "half-true": 0,
                "barely-true": 1,
                "false": 1,
                "pants-fire": 1,
            },
            "positive_class": 1,
            "positive_class_meaning": "misinformation-risk label (barely-true / false / pants-fire)",
            "score_threshold": args.score_threshold,
        },
        "hybrid_scoring": {
            "formula": "0.5 * Logistic Regression + 0.3 * Random Forest + 0.2 * DistilBERT",
            "medium_risk_threshold": args.medium_risk_threshold,
            "high_risk_threshold": args.high_risk_threshold,
        },
        "record_count": len(records),
        "models": model_metrics,
        "hybrid_risk_distribution": risk_level_counts,
        "comparison_table": comparison_rows,
    }

    (report_dir / "benchmark.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    write_csv(report_dir, comparison_rows)
    write_markdown(report_dir, comparison_rows)

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
