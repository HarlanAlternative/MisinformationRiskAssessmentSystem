from __future__ import annotations

import re
import csv
from pathlib import Path


def normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


LIAR_LABEL_MAP = {
    "true": 0,
    "mostly-true": 0,
    "half-true": 0,
    "barely-true": 1,
    "false": 1,
    "pants-fire": 1,
}


def load_liar(dataset_root: str | Path) -> list[dict[str, object]]:
    root = Path(dataset_root)
    if not root.exists():
        raise FileNotFoundError(f"Dataset root not found: {root}")

    records: list[dict[str, object]] = []
    for split_name in ("train.tsv", "valid.tsv", "test.tsv"):
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

                statement = normalize_text(row[2])
                subject = normalize_text(row[3])
                speaker = normalize_text(row[4])
                speaker_job = normalize_text(row[5])
                state_info = normalize_text(row[6])
                party = normalize_text(row[7])
                context = normalize_text(row[13])

                text = " [SEP] ".join(
                    segment
                    for segment in [statement, subject, speaker, speaker_job, state_info, party, context]
                    if segment
                )
                if not statement:
                    continue

                records.append(
                    {
                        "text": text,
                        "label": LIAR_LABEL_MAP[label_name],
                        "original_label": label_name,
                        "split": split_name.replace(".tsv", ""),
                    }
                )

    if not records:
        raise RuntimeError("No LIAR records were loaded for DistilBERT training.")

    return records
