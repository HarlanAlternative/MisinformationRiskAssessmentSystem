from __future__ import annotations

import ast
import hashlib
import inspect
import json
import re
import csv
import textwrap
from pathlib import Path
from typing import Iterable

# Bump when the artifact metrics.json layout changes. Artifacts written under an
# older version cannot be validated and must be retrained.
ARTIFACT_SCHEMA_VERSION = 2

EMOTIONAL_WORDS = {
    "amazing",
    "angry",
    "astonishing",
    "bombshell",
    "breaking",
    "crisis",
    "danger",
    "disaster",
    "fear",
    "furious",
    "hate",
    "incredible",
    "massive",
    "miracle",
    "panic",
    "rage",
    "scandal",
    "secret",
    "shocking",
    "terrifying",
    "urgent",
}

EXAGGERATION_WORDS = {
    "always",
    "completely",
    "everyone",
    "guaranteed",
    "must-see",
    "never",
    "nobody",
    "proof",
    "totally",
    "unbelievable",
    "undeniable",
}

WORD_RE = re.compile(r"\b[\w'-]+\b")

LIAR_LABEL_MAP = {
    "true": 0,
    "mostly-true": 0,
    "half-true": 0,
    "barely-true": 1,
    "false": 1,
    "pants-fire": 1,
}


def normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def compose_text(title: str | None, content: str | None, source: str | None = None) -> str:
    segments = [normalize_text(title), normalize_text(content), normalize_text(source)]
    return " ".join(segment for segment in segments if segment)


def extract_rule_features(title: str | None, content: str | None, source: str | None = None) -> dict[str, float]:
    combined = compose_text(title, content, None)
    words = WORD_RE.findall(combined)
    total_letters = sum(character.isalpha() for character in combined)
    uppercase_letters = sum(character.isupper() for character in combined)
    punctuation_count = sum(character in "!?.,;:-'\"" for character in combined)
    emotional_count = sum(word.lower() in EMOTIONAL_WORDS for word in words)
    exaggeration_count = sum(word.lower() in EXAGGERATION_WORDS for word in words)

    return {
        "text_length": float(len(combined)),
        "word_count": float(len(words)),
        "punctuation_count": float(punctuation_count),
        "emotional_word_ratio": float(emotional_count / len(words)) if words else 0.0,
        "uppercase_ratio": float(uppercase_letters / total_letters) if total_letters else 0.0,
        "exclamation_count": float(combined.count("!")),
        "exaggeration_count": float(exaggeration_count),
        "has_source": 1.0 if normalize_text(source) else 0.0,
    }


def load_liar_records(dataset_root: str | Path) -> list[dict[str, object]]:
    root = Path(dataset_root)
    if not root.exists():
        raise FileNotFoundError(f"LIAR dataset path does not exist: {root}")

    records: list[dict[str, object]] = []
    split_files = ("train.tsv", "valid.tsv", "test.tsv")

    for split_name in split_files:
        split_path = root / split_name
        if not split_path.exists():
            continue

        with split_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle, delimiter="\t")
            for row in reader:
                if len(row) < 14:
                    continue

                label_name = normalize_text(row[1]).lower()
                if label_name not in LIAR_LABEL_MAP:
                    continue

                title = normalize_text(row[2])
                subject = normalize_text(row[3])
                speaker = normalize_text(row[4])
                speaker_job = normalize_text(row[5])
                state_info = normalize_text(row[6])
                party = normalize_text(row[7])
                context = normalize_text(row[13])

                # LIAR columns 8-12 are the speaker's credit-history counts. They are
                # tallied *including* the current statement, so the row's own label is
                # recoverable from them. Excluded from the model input as label leakage.
                content = normalize_text(" ".join(part for part in [subject, context, speaker_job, state_info] if part))
                source = normalize_text(" ".join(part for part in [speaker, party] if part))

                if not title:
                    continue

                records.append(
                    {
                        "title": title,
                        "content": content,
                        "source": source,
                        "text": compose_text(title, content, source),
                        "label": LIAR_LABEL_MAP[label_name],
                        "split": split_name.replace(".tsv", ""),
                        "original_label": label_name,
                    }
                )

    if not records:
        raise RuntimeError(
            "No training records were loaded from LIAR. "
            "Confirm the repository contents and folder layout."
        )

    return records


def feature_matrix(records: Iterable[dict[str, object]], include_source: bool = True) -> list[list[float]]:
    vectors: list[list[float]] = []
    for record in records:
        signals = extract_rule_features(
            record.get("title"),
            record.get("content"),
            record.get("source") if include_source else None,
        )
        vectors.append(list(signals.values()))
    return vectors


def feature_names() -> list[str]:
    return [
        "text_length",
        "word_count",
        "punctuation_count",
        "emotional_word_ratio",
        "uppercase_ratio",
        "exclamation_count",
        "exaggeration_count",
        "has_source",
    ]


def pipeline_fingerprint() -> str:
    """Hash the code that decides what a feature vector means.

    Stored in the artifact metrics.json at training time and re-checked when the
    artifacts are loaded for evaluation. If someone edits how records are parsed
    or features are derived and does not retrain, the saved models no longer match
    the code scoring them, and every number produced from them is silently wrong.
    Comparing this hash turns that into a loud failure.

    Sources are reduced to their AST, so comments and reformatting do not
    invalidate otherwise identical artifacts.
    """
    parts: list[str] = []
    for function in (normalize_text, compose_text, extract_rule_features, load_liar_records, feature_names):
        tree = ast.parse(textwrap.dedent(inspect.getsource(function)))
        parts.append(ast.dump(tree, annotate_fields=True, include_attributes=False))

    parts.append(repr(sorted(LIAR_LABEL_MAP.items())))
    parts.append(repr(sorted(EMOTIONAL_WORDS)))
    parts.append(repr(sorted(EXAGGERATION_WORDS)))
    parts.append(WORD_RE.pattern)

    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()[:16]
