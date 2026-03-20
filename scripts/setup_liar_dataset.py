#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "data" / "liar"
DEFAULT_URLS = [
    "https://www.cs.ucsb.edu/~william/data/liar_dataset.zip",
]
REQUIRED_FILES = ["train.tsv", "valid.tsv", "test.tsv"]


def dataset_ready(directory: Path) -> bool:
    return all((directory / filename).exists() for filename in REQUIRED_FILES)


def download_zip(url: str, destination: Path) -> None:
    try:
        with urllib.request.urlopen(url, timeout=60) as response, destination.open("wb") as output_file:
            shutil.copyfileobj(response, output_file)
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to download LIAR dataset from {url}: {exc}") from exc


def normalize_extracted_dataset(staging_dir: Path, output_dir: Path) -> None:
    candidates = [path for path in staging_dir.rglob("train.tsv") if path.is_file()]
    if not candidates:
        raise RuntimeError(
            "Downloaded archive did not contain train.tsv. "
            "Manually place train.tsv, valid.tsv, and test.tsv into data/liar."
        )

    source_root = candidates[0].parent
    output_dir.mkdir(parents=True, exist_ok=True)

    for filename in REQUIRED_FILES:
        source_file = source_root / filename
        if not source_file.exists():
            raise RuntimeError(f"Dataset archive is missing {filename}.")
        shutil.copy2(source_file, output_dir / filename)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download and normalize the LIAR dataset into data/liar.")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where train.tsv, valid.tsv, and test.tsv will be placed.",
    )
    parser.add_argument(
        "--zip-file",
        default="",
        help="Optional path to a pre-downloaded liar_dataset.zip file.",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    if dataset_ready(output_dir):
        print(f"LIAR dataset already prepared at {output_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temporary_directory:
        temp_dir = Path(temporary_directory)
        archive_path = temp_dir / "liar_dataset.zip"

        if args.zip_file:
            source_zip = Path(args.zip_file).resolve()
            if not source_zip.exists():
                raise SystemExit(f"Provided --zip-file path does not exist: {source_zip}")
            shutil.copy2(source_zip, archive_path)
        else:
            download_errors: list[str] = []
            for url in DEFAULT_URLS:
                try:
                    print(f"Downloading LIAR dataset from {url}")
                    download_zip(url, archive_path)
                    break
                except Exception as exc:  # noqa: BLE001
                    download_errors.append(str(exc))
            else:
                message = [
                    "Unable to download the LIAR dataset automatically.",
                    *download_errors,
                    "Manual fallback:",
                    "1. Download liar_dataset.zip from https://www.cs.ucsb.edu/~william/data/liar_dataset.zip",
                    "2. Re-run this script with --zip-file /path/to/liar_dataset.zip",
                    "3. Or place train.tsv, valid.tsv, and test.tsv directly into data/liar",
                ]
                raise SystemExit("\n".join(message))

        try:
            with zipfile.ZipFile(archive_path, "r") as archive:
                archive.extractall(temp_dir / "extracted")
        except zipfile.BadZipFile as exc:
            raise SystemExit(f"The LIAR dataset archive is invalid: {archive_path}") from exc

        normalize_extracted_dataset(temp_dir / "extracted", output_dir)

    if not dataset_ready(output_dir):
        raise SystemExit(f"Dataset setup failed. Expected files were not created in {output_dir}")

    print(f"LIAR dataset is ready at {output_dir}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(130)
