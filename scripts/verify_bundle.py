#!/usr/bin/env python3
"""Check an extracted artifact bundle against its manifest.

Run inside a container build after downloading a release bundle. A truncated
download or a mismatched release tag otherwise produces an image that starts
and serves confident scores from the wrong weights.

    python scripts/verify_bundle.py <extracted-dir> [--expect-fingerprint HASH]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path


def digest(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify an extracted artifact bundle.")
    parser.add_argument("bundle_dir")
    parser.add_argument("--expect-fingerprint", default="")
    args = parser.parse_args()

    bundle_dir = Path(args.bundle_dir)
    manifest_path = bundle_dir / "manifest.json"
    if not manifest_path.exists():
        print(f"ERROR: no manifest.json in '{bundle_dir}'; bundle is not verifiable.", file=sys.stderr)
        return 1

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    failures: list[str] = []

    for name, expected in manifest.get("files", {}).items():
        target = bundle_dir / name
        if not target.exists():
            failures.append(f"missing file: {name}")
            continue
        actual = digest(target)
        if actual != expected:
            failures.append(f"digest mismatch: {name} (expected {expected[:12]}, got {actual[:12]})")

    if args.expect_fingerprint:
        recorded = manifest.get("pipeline_fingerprint")
        if recorded != args.expect_fingerprint:
            failures.append(
                f"pipeline fingerprint mismatch: bundle {recorded!r}, expected {args.expect_fingerprint!r}"
            )

    if failures:
        print(f"ERROR: bundle '{manifest.get('bundle')}' failed verification:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    print(f"Bundle '{manifest.get('bundle')}' verified: {len(manifest.get('files', {}))} files match the manifest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
