#!/usr/bin/env python3
"""Bundle trained model artifacts for container builds.

Model files are too large for git and are not tracked, so container images have
no way to obtain them from a checkout alone. This packages them into two
tarballs to be attached to a GitHub release, which the Dockerfiles then download
by tag at build time.

Each tarball carries a manifest recording the pipeline fingerprint and per-file
SHA-256 digests, so a build can tell whether it received the artifacts it expected
rather than trusting whatever was at the URL.

    python scripts/package_artifacts.py --output-dir dist

Then attach dist/*.tar.gz to a release and build with a matching
--build-arg ARTIFACT_RELEASE_TAG.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
ML_DIR = REPO_ROOT / "backend" / "Services" / "Ml"
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from common import ARTIFACT_SCHEMA_VERSION, pipeline_fingerprint  # noqa: E402

CLASSICAL_FILES = (
    "tfidf_vectorizer.joblib",
    "logistic_regression.joblib",
    "random_forest.joblib",
    "metrics.json",
)

# Everything the checkpoint needs to serve. Training checkpoints and optimizer
# state are deliberately excluded: they are large and useless at inference.
BERT_FILES = (
    "config.json",
    "model.safetensors",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "vocab.txt",
    "model_info.json",
    "metrics.json",
)


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def build_bundle(name: str, source_dir: Path, members: tuple[str, ...], output_dir: Path, extra: dict) -> dict:
    missing = [member for member in members if not (source_dir / member).exists()]
    if missing:
        raise SystemExit(
            f"Cannot package '{name}': missing {', '.join(missing)} under '{source_dir}'. "
            "Train the models first (scripts/train_all.ps1 or train_all.sh)."
        )

    manifest = {
        "bundle": name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "schema_version": ARTIFACT_SCHEMA_VERSION,
        "files": {member: digest(source_dir / member) for member in members},
        **extra,
    }

    manifest_path = output_dir / f"{name}.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    archive_path = output_dir / f"{name}.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        for member in members:
            archive.add(source_dir / member, arcname=member)
        archive.add(manifest_path, arcname="manifest.json")

    size_mb = archive_path.stat().st_size / 1e6
    print(f"  {archive_path.name:<28} {size_mb:7.1f} MB  ({len(members)} files)")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Package trained artifacts for container builds.")
    parser.add_argument("--classical-artifact-dir", default=str(ML_DIR / "artifacts"))
    parser.add_argument("--bert-model-dir", default=str(REPO_ROOT / "bert_service" / "models" / "distilbert-liar"))
    parser.add_argument("--output-dir", default=str(REPO_ROOT / "dist"))
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    bert_dir = Path(args.bert_model_dir)
    bert_info = json.loads((bert_dir / "model_info.json").read_text(encoding="utf-8")) if (
        bert_dir / "model_info.json"
    ).exists() else {}
    if bert_info.get("mode") == "pretrained":
        raise SystemExit(
            f"'{bert_dir}' holds the SST-2 startup placeholder, not a LIAR fine-tune. "
            "Packaging it would ship a model unrelated to the task. "
            "Fine-tune first with 'bert_service/train.py --mode train'."
        )

    print("Packaging artifacts:")
    fingerprint = pipeline_fingerprint()
    build_bundle(
        "classical-artifacts",
        Path(args.classical_artifact_dir),
        CLASSICAL_FILES,
        output_dir,
        {"pipeline_fingerprint": fingerprint},
    )
    build_bundle(
        "distilbert-liar",
        bert_dir,
        BERT_FILES,
        output_dir,
        {"model_info": bert_info},
    )

    print(f"\nPipeline fingerprint: {fingerprint}")
    print(f"Output: {output_dir}")
    print("\nAttach both .tar.gz files to a release, then build images with a matching")
    print("--build-arg ARTIFACT_RELEASE_TAG=<tag>.")


if __name__ == "__main__":
    main()
