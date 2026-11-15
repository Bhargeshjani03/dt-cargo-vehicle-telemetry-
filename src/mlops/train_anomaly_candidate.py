"""Train and publish a versioned anomaly-model candidate to Kuberns Storage."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests


REPO_ROOT = Path(__file__).resolve().parents[2]
TRAINING_SCRIPT = REPO_ROOT / "src/anomaly_detection/src/train.py"
GATEWAY = "https://gateway.kuberns.cloud"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _object_url(bucket: str, key: str) -> str:
    path = Path(key)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError("Kuberns object keys must be relative and stay inside the bucket.")
    return f"{GATEWAY}/{quote(bucket, safe='')}/{quote(path.as_posix(), safe='/')}"


def _download_training_data(bucket: str, key: str, auth: tuple[str, str], destination: Path) -> None:
    try:
        with requests.get(_object_url(bucket, key), auth=auth, timeout=(15, 300), stream=True) as response:
            response.raise_for_status()
            with destination.open("wb") as output:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        output.write(chunk)
    except requests.RequestException as exc:
        raise RuntimeError(
            "Could not download the configured anomaly training data from Kuberns Storage. "
            "Check the bucket, object key, and read credential."
        ) from exc


def _upload_file(bucket: str, key: str, auth: tuple[str, str], path: Path) -> None:
    content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    try:
        with path.open("rb") as file:
            response = requests.put(
                _object_url(bucket, key),
                data=file,
                auth=auth,
                headers={"Content-Type": content_type},
                timeout=(15, 300),
            )
            response.raise_for_status()
    except requests.RequestException as exc:
        raise RuntimeError(f"Could not publish candidate file {key} to Kuberns Storage.") from exc


def _check_summary(summary_path: Path) -> dict:
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    expected = {"cluster_0", "cluster_1", "cluster_2"}
    if set(summary) != expected:
        raise ValueError(f"Expected candidate summaries for clusters 0, 1, and 2; got {sorted(summary)}.")
    for name, model_summary in summary.items():
        policy = model_summary.get("threshold_policy", {})
        required = ("threshold", "training_tracks", "validation_tracks")
        if any(model_summary.get(field) is None for field in required):
            raise ValueError(f"Candidate summary {name} is missing required validation metadata.")
        if not policy.get("calibration") or policy.get("actual_validation_alert_rate") is None:
            raise ValueError(f"Candidate summary {name} is missing its alert-rate calibration details.")
    return summary


def main() -> None:
    bucket = os.environ.get("KUBERNS_BUCKET_ID", "").strip()
    access_key = os.environ.get("KUBERNS_ACCESS_KEY_ID", "").strip()
    secret = os.environ.get("KUBERNS_SECRET", "").strip()
    training_key = os.environ.get("KUBERNS_TRAINING_KEY", "").strip() or "training/anomaly/modeling_dataset.csv"
    candidate_prefix = os.environ.get("KUBERNS_CANDIDATE_PREFIX", "").strip("/") or "models/anomaly/candidates"
    run_id = os.environ.get("DT_CARGO_RUN_ID", "manual-local-run").strip()
    review_rate = os.environ.get("DT_CARGO_REVIEW_RATE", "0.02")
    validation_fraction = os.environ.get("DT_CARGO_VALIDATION_FRACTION", "0.20")
    if not all((bucket, access_key, secret)):
        raise RuntimeError("Set KUBERNS_BUCKET_ID, KUBERNS_ACCESS_KEY_ID, and KUBERNS_SECRET.")
    auth = (access_key, secret)

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    safe_run_id = "".join(character if character.isalnum() or character in "-_" else "-" for character in run_id)
    candidate_id = f"{timestamp}-{safe_run_id}"

    with tempfile.TemporaryDirectory(prefix="dt-cargo-ct-") as temp_dir:
        work = Path(temp_dir)
        input_path = work / "modeling_dataset.csv"
        report_dir = work / "reports"
        artifact_dir = work / "artifacts"
        _download_training_data(bucket, training_key, auth, input_path)
        input_hash = _sha256(input_path)

        subprocess.run(
            [
                sys.executable,
                str(TRAINING_SCRIPT),
                "--input-csv", str(input_path),
                "--report-dir", str(report_dir),
                "--artifact-dir", str(artifact_dir),
                "--review-rate", review_rate,
                "--validation-fraction", validation_fraction,
            ],
            cwd=REPO_ROOT,
            check=True,
        )

        summary_path = report_dir / "validation_summary.json"
        summary = _check_summary(summary_path)
        artifacts = sorted(artifact_dir.glob("isolation_forest_cluster_*_v1.joblib"))
        if len(artifacts) != 3:
            raise ValueError(f"Expected three cluster artifacts, found {len(artifacts)}.")

        manifest = {
            "candidate_id": candidate_id,
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_commit": os.environ.get("GITHUB_SHA", "unknown"),
            "training_object": training_key,
            "training_data_sha256": input_hash,
            "review_rate": float(review_rate),
            "validation_fraction": float(validation_fraction),
            "validation_summary": summary,
            "artifacts": {path.name: _sha256(path) for path in artifacts},
            "promotion_status": "candidate_requires_human_review",
        }
        manifest_path = report_dir / "candidate_manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        prefix = f"{candidate_prefix}/{candidate_id}"
        for path in [*artifacts, summary_path, manifest_path]:
            key = f"{prefix}/{path.name}"
            _upload_file(bucket, key, auth, path)
            print(f"Published candidate object: {key}")

        print(f"Candidate {candidate_id} is available for review; it was not promoted.")


if __name__ == "__main__":
    main()
