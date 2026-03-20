from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from datasets import Dataset
from sklearn.metrics import accuracy_score, precision_recall_fscore_support
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

from data_utils import LIAR_LABEL_MAP, load_liar

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET_ROOT = REPO_ROOT / "data" / "liar"
DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent / "models" / "distilbert-liar"
DEFAULT_PRETRAINED_MODEL = "distilbert-base-uncased-finetuned-sst-2-english"


def tokenize_batch(tokenizer, batch):
    return tokenizer(batch["text"], truncation=True, max_length=256)


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=-1)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels,
        predictions,
        average="binary",
        zero_division=0,
    )
    return {
        "accuracy": round(float(accuracy_score(labels, predictions)), 4),
        "precision": round(float(precision), 4),
        "recall": round(float(recall), 4),
        "f1": round(float(f1), 4),
    }


def split_records(records: list[dict[str, object]]) -> dict[str, list[dict[str, object]]]:
    grouped: dict[str, list[dict[str, object]]] = {"train": [], "valid": [], "test": []}
    for record in records:
        split_name = str(record.get("split", "")).lower()
        if split_name in grouped:
            grouped[split_name].append(record)
    return grouped


def build_dataset(records: list[dict[str, object]], tokenizer):
    dataset = Dataset.from_list(records)
    return dataset.map(lambda batch: tokenize_batch(tokenizer, batch), batched=True)


def evaluate_checkpoint(
    model_reference: str,
    dataset_root: str | Path,
    output_dir: Path,
    max_length: int,
) -> dict[str, object]:
    records = load_liar(dataset_root)
    records_by_split = split_records(records)
    valid_records = records_by_split["valid"]
    test_records = records_by_split["test"]

    if not valid_records or not test_records:
        raise SystemExit(
            "Expected LIAR valid and test splits for DistilBERT evaluation. "
            f"Found counts: valid={len(valid_records)}, test={len(test_records)}."
        )

    tokenizer = AutoTokenizer.from_pretrained(model_reference)
    model = AutoModelForSequenceClassification.from_pretrained(model_reference)
    data_collator = DataCollatorWithPadding(tokenizer=tokenizer)

    valid_dataset = build_dataset(valid_records, tokenizer)
    test_dataset = build_dataset(test_records, tokenizer)

    args = TrainingArguments(
        output_dir=str(output_dir / "eval"),
        per_device_eval_batch_size=8,
        report_to="none",
    )
    trainer = Trainer(
        model=model,
        args=args,
        tokenizer=tokenizer,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
    )

    valid_metrics = trainer.predict(valid_dataset).metrics
    test_metrics = trainer.predict(test_dataset).metrics

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "dataset": "LIAR",
        "evaluation_protocol": {
            "train_split": "train.tsv",
            "validation_split": "valid.tsv",
            "test_split": "test.tsv",
            "label_mapping": LIAR_LABEL_MAP,
            "positive_class": 1,
            "positive_class_meaning": "misinformation-risk label (barely-true / false / pants-fire)",
            "token_max_length": max_length,
        },
        "record_counts": {
            "train": len(records_by_split["train"]),
            "valid": len(valid_records),
            "test": len(test_records),
            "total": len(records),
        },
        "metrics": {
            "valid": {
                "accuracy": round(float(valid_metrics["test_accuracy"]), 4),
                "precision": round(float(valid_metrics["test_precision"]), 4),
                "recall": round(float(valid_metrics["test_recall"]), 4),
                "f1": round(float(valid_metrics["test_f1"]), 4),
            },
            "test": {
                "accuracy": round(float(test_metrics["test_accuracy"]), 4),
                "precision": round(float(test_metrics["test_precision"]), 4),
                "recall": round(float(test_metrics["test_recall"]), 4),
                "f1": round(float(test_metrics["test_f1"]), 4),
            },
        },
    }


def prepare_pretrained_model(output_dir: Path, model_name: str) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    tokenizer.save_pretrained(output_dir)
    model.save_pretrained(output_dir)
    metadata = {
        "mode": "pretrained",
        "source_model": model_name,
        "note": "Fallback development model prepared for local startup. Replace with a LIAR fine-tuned checkpoint for project-quality predictions.",
    }
    (output_dir / "model_info.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare, fine-tune, or evaluate DistilBERT for the LIAR dataset.")
    parser.add_argument(
        "--dataset-root",
        default=str(DEFAULT_DATASET_ROOT),
        help="Path to the LIAR dataset root. Defaults to data/liar under the repository root.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for the prepared or fine-tuned DistilBERT checkpoint.",
    )
    parser.add_argument(
        "--mode",
        choices=["train", "pretrained", "evaluate"],
        default=os.getenv("BERT_SETUP_MODE", "pretrained"),
        help="Use 'train' to fine-tune on LIAR, 'pretrained' to download a local fallback checkpoint, or 'evaluate' to evaluate an existing checkpoint.",
    )
    parser.add_argument("--model-name", default="distilbert-base-uncased")
    parser.add_argument("--pretrained-model-name", default=DEFAULT_PRETRAINED_MODEL)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-length", type=int, default=int(os.getenv("BERT_MAX_LENGTH", "256")))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "pretrained":
        metadata = prepare_pretrained_model(output_dir, args.pretrained_model_name)
        metrics = evaluate_checkpoint(str(output_dir), args.dataset_root, output_dir, args.max_length)
        metrics["mode"] = "pretrained"
        metrics["model_reference"] = str(output_dir)
        metrics["model_info"] = metadata
        (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        print(json.dumps(metrics, indent=2))
        return

    if args.mode == "evaluate":
        metrics = evaluate_checkpoint(str(output_dir), args.dataset_root, output_dir, args.max_length)
        metrics["mode"] = "evaluate"
        metrics["model_reference"] = str(output_dir)
        (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        print(json.dumps(metrics, indent=2))
        return

    try:
        records = load_liar(args.dataset_root)
    except Exception as exc:
        raise SystemExit(
            "Unable to load the LIAR dataset for DistilBERT training. "
            f"Expected train.tsv, valid.tsv, and test.tsv under '{args.dataset_root}'. "
            "Run scripts/setup_liar_dataset.py first, or rerun this command with --mode pretrained."
        ) from exc

    records_by_split = split_records(records)
    train_records = records_by_split["train"]
    valid_records = records_by_split["valid"]

    if not train_records or not valid_records:
        raise SystemExit(
            "Expected LIAR train and valid splits for DistilBERT training. "
            f"Found counts: train={len(train_records)}, valid={len(valid_records)}."
        )

    tokenizer = AutoTokenizer.from_pretrained(args.model_name)
    train_dataset = build_dataset(train_records, tokenizer)
    valid_dataset = build_dataset(valid_records, tokenizer)

    model = AutoModelForSequenceClassification.from_pretrained(args.model_name, num_labels=2)
    training_args = TrainingArguments(
        output_dir=str(output_dir),
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=2e-5,
        num_train_epochs=args.epochs,
        evaluation_strategy="epoch",
        save_strategy="epoch",
        load_best_model_at_end=True,
        metric_for_best_model="f1",
        weight_decay=0.01,
        logging_steps=50,
        report_to="none",
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=valid_dataset,
        tokenizer=tokenizer,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=compute_metrics,
    )

    trainer.train()
    trainer.save_model(output_dir)
    tokenizer.save_pretrained(output_dir)

    model_info = {
        "mode": "train",
        "base_model": args.model_name,
        "dataset_root": str(Path(args.dataset_root).resolve()),
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "max_length": args.max_length,
    }
    (output_dir / "model_info.json").write_text(json.dumps(model_info, indent=2), encoding="utf-8")

    metrics = evaluate_checkpoint(str(output_dir), args.dataset_root, output_dir, args.max_length)
    metrics["mode"] = "train"
    metrics["model_reference"] = str(output_dir)
    metrics["model_info"] = model_info
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
