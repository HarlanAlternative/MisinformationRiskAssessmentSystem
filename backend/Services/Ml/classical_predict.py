from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
from scipy.sparse import csr_matrix, hstack

from common import extract_rule_features


def build_input_vector(vectorizer, title: str, content: str, source: str):
    combined_text = " ".join(part for part in [title, content, source] if part).strip()
    tfidf = vectorizer.transform([combined_text])
    numeric_features = extract_rule_features(title, content, source)
    numeric = csr_matrix(np.asarray([list(numeric_features.values())], dtype=np.float64))
    return hstack([tfidf, numeric]).tocsr(), tfidf


def top_terms(vectorizer, logistic_model, tfidf_row, limit: int = 5) -> list[str]:
    if tfidf_row.nnz == 0:
        return []

    feature_names = vectorizer.get_feature_names_out()
    coefficients = logistic_model.coef_[0][: len(feature_names)]
    indices = tfidf_row.indices
    weights = tfidf_row.data * coefficients[indices]
    ranked = sorted(zip(indices, weights), key=lambda item: item[1], reverse=True)
    return [feature_names[index] for index, score in ranked[:limit] if score > 0]


def main() -> None:
    parser = argparse.ArgumentParser(description="Score a single claim with classical models.")
    parser.add_argument("--model-dir", required=True, help="Directory containing classical model artifacts.")
    args = parser.parse_args()

    payload = json.loads(sys.stdin.read())
    title = (payload.get("title") or "").strip()
    content = (payload.get("content") or "").strip()
    source = (payload.get("source") or "").strip()

    model_dir = Path(args.model_dir)
    required_files = [
        model_dir / "tfidf_vectorizer.joblib",
        model_dir / "logistic_regression.joblib",
        model_dir / "random_forest.joblib",
    ]

    missing_files = [str(path) for path in required_files if not path.exists()]
    if missing_files:
        raise SystemExit(
            "Classical model artifacts are missing. "
            f"Expected files: {', '.join(missing_files)}. "
            "Run backend/Services/Ml/train_classical_models.py first."
        )

    vectorizer = joblib.load(model_dir / "tfidf_vectorizer.joblib")
    logistic = joblib.load(model_dir / "logistic_regression.joblib")
    random_forest = joblib.load(model_dir / "random_forest.joblib")

    features, tfidf_row = build_input_vector(vectorizer, title, content, source)
    logistic_score = float(logistic.predict_proba(features)[0, 1])
    random_forest_score = float(random_forest.predict_proba(features)[0, 1])

    result = {
        "logisticScore": round(logistic_score, 4),
        "randomForestScore": round(random_forest_score, 4),
        "topTerms": top_terms(vectorizer, logistic, tfidf_row[0], limit=5),
    }
    sys.stdout.write(json.dumps(result))


if __name__ == "__main__":
    main()
