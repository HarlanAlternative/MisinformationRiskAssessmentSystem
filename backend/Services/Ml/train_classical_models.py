from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score

from common import LIAR_LABEL_MAP, feature_matrix, feature_names, load_liar_records

DEFAULT_DATASET_ROOT = Path(__file__).resolve().parents[3] / "data" / "liar"


def build_sparse_matrix(vectorizer: TfidfVectorizer, texts: list[str], numeric_rows: list[list[float]], fit: bool):
    tfidf = vectorizer.fit_transform(texts) if fit else vectorizer.transform(texts)
    numeric = csr_matrix(np.asarray(numeric_rows, dtype=np.float64))
    return hstack([tfidf, numeric]).tocsr()


def split_records(records: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {"train": [], "valid": [], "test": []}
    for record in records:
        split_name = str(record.get("split", "")).lower()
        if split_name in grouped:
            grouped[split_name].append(record)
    return grouped


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


def evaluate_model(
    vectorizer: TfidfVectorizer,
    model,
    records: list[dict[str, object]],
) -> dict[str, float | None]:
    texts = [str(record["text"]) for record in records]
    numeric_rows = feature_matrix(records)
    labels = np.asarray([int(record["label"]) for record in records], dtype=np.int64)
    features = build_sparse_matrix(vectorizer, texts, numeric_rows, fit=False)
    scores = model.predict_proba(features)[:, 1]
    return compute_binary_metrics(labels, scores)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train classical misinformation models on the LIAR dataset.")
    parser.add_argument(
        "--dataset-root",
        default=str(DEFAULT_DATASET_ROOT),
        help="Path to the LIAR dataset root. Defaults to data/liar under the repository root.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parent / "artifacts"),
        help="Directory where model artifacts will be written.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        records = load_liar_records(args.dataset_root)
    except Exception as exc:
        raise SystemExit(
            "Unable to load the LIAR dataset. "
            f"Expected train.tsv, valid.tsv, and test.tsv under '{args.dataset_root}'. "
            "Run scripts/setup_liar_dataset.py first."
        ) from exc

    records_by_split = split_records(records)
    train_records = records_by_split["train"]
    valid_records = records_by_split["valid"]
    test_records = records_by_split["test"]

    if not train_records or not valid_records or not test_records:
        raise SystemExit(
            "Expected LIAR train, valid, and test splits to be present. "
            f"Found counts: train={len(train_records)}, valid={len(valid_records)}, test={len(test_records)}."
        )

    train_texts = [str(record["text"]) for record in train_records]
    train_numeric = feature_matrix(train_records)
    y_train = np.asarray([int(record["label"]) for record in train_records], dtype=np.int64)

    vectorizer = TfidfVectorizer(
        max_features=25000,
        ngram_range=(1, 2),
        min_df=2,
        stop_words="english",
        sublinear_tf=True,
    )

    x_train = build_sparse_matrix(vectorizer, train_texts, train_numeric, fit=True)

    logistic = LogisticRegression(
        max_iter=2000,
        class_weight="balanced",
        solver="liblinear",
        random_state=42,
    )
    logistic.fit(x_train, y_train)

    random_forest = RandomForestClassifier(
        n_estimators=400,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=42,
    )
    random_forest.fit(x_train, y_train)

    metrics = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "LIAR",
        "evaluation_protocol": {
            "train_split": "train.tsv",
            "validation_split": "valid.tsv",
            "test_split": "test.tsv",
            "label_mapping": LIAR_LABEL_MAP,
            "positive_class": 1,
            "positive_class_meaning": "misinformation-risk label (barely-true / false / pants-fire)",
        },
        "record_counts": {
            "train": len(train_records),
            "valid": len(valid_records),
            "test": len(test_records),
            "total": len(records),
        },
        "models": {
            "logisticRegression": {
                "valid": evaluate_model(vectorizer, logistic, valid_records),
                "test": evaluate_model(vectorizer, logistic, test_records),
            },
            "randomForest": {
                "valid": evaluate_model(vectorizer, random_forest, valid_records),
                "test": evaluate_model(vectorizer, random_forest, test_records),
            },
        },
        "numeric_feature_names": feature_names(),
    }

    joblib.dump(vectorizer, output_dir / "tfidf_vectorizer.joblib")
    joblib.dump(logistic, output_dir / "logistic_regression.joblib")
    joblib.dump(random_forest, output_dir / "random_forest.joblib")
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(
        json.dumps(
            {
                "artifacts": {
                    "tfidf_vectorizer": str(output_dir / "tfidf_vectorizer.joblib"),
                    "logistic_regression": str(output_dir / "logistic_regression.joblib"),
                    "random_forest": str(output_dir / "random_forest.joblib"),
                    "metrics": str(output_dir / "metrics.json"),
                },
                "metrics": metrics,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
