"""Share lightweight run logging and CSV export across pipeline stages.

Shared by the pipeline stages. Samples, variable definitions, models
and estimators are deliberately absent from this module.
"""

from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import logging
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import pandas as pd


def begin_stage(
    result_dir: Path,
    input_files: Sequence[Path],
    seed: int | None,
    upstream_stages: Sequence[str] = (),
    *,
    new_run: bool = False,
) -> dict[str, Any]:
    """Record a stage start and require its upstream stages to be complete.

    The first stage resets the shared log and records the environment once.
    An exception leaves the stage incomplete. Source checksums and analytical
    checks stay visible in the scripts; intermediate files are not hashed.
    """
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format=f"[{result_dir.name}] %(message)s",
        handlers=[
            logging.FileHandler(
                log_dir / "practices.log", mode="w" if new_run else "a"
            ),
            logging.StreamHandler(sys.stdout),
        ],
        force=True,
    )
    started = datetime.now(timezone.utc)
    run_path = log_dir / "run.json"
    if new_run:
        with Path("environment.yml").open("rb") as handle:
            environment_hash = hashlib.file_digest(
                handle, "sha256"
            ).hexdigest()
        run = {
            "run_id": started.strftime("%Y%m%dT%H%M%S%fZ"),
            "started_at_utc": started.isoformat(),
            "executable": sys.executable,
            "python": sys.version,
            "packages": {
                name: version(name)
                for name in (
                    "numpy",
                    "pandas",
                    "pyarrow",
                    "scipy",
                    "statsmodels",
                    "matplotlib",
                )
            },
            "environment_sha256": environment_hash,
            "stages": {},
        }
    else:
        run = json.loads(run_path.read_text())
    run["status"] = "incomplete"
    run.pop("completed_at_utc", None)
    manifest = {
        "stage": result_dir.name,
        "run_id": started.strftime("%Y%m%dT%H%M%S%fZ"),
        "status": "incomplete",
        "started_at_utc": started.isoformat(),
        "seed": seed,
        "command": sys.argv,
        "inputs": [str(path) for path in input_files],
        "upstream_stages": list(upstream_stages),
    }
    run["stages"][result_dir.name] = manifest
    run_path.write_text(json.dumps(run, indent=2) + "\n")
    logging.info("Stage %s; run %s", result_dir.name, manifest["run_id"])
    for name in upstream_stages:
        if run["stages"][name]["status"] != "complete":
            raise ValueError(
                f"{name}: upstream stage is not complete in {run_path}"
            )
    for path in input_files:
        logging.info("Reading %s", path)
    return manifest


def write_tables(
    tables: Mapping[str, pd.DataFrame], directory: Path
) -> list[Path]:
    """Write every table as CSV and return the paths for its stage record.

    Stages 3 and 5 write their two selected Parquet exports explicitly.
    """
    directory.mkdir(parents=True, exist_ok=True)
    outputs = []
    for name, table in tables.items():
        csv_path = directory / f"{name}.csv"
        # Keep empty strings distinct from missing values, and preserve NA
        # as Namibia's valid identifier when consumers disable default NA parsing.
        table.to_csv(csv_path, index=False, na_rep="<NA>")
        outputs.append(csv_path)
    return outputs


def finish_stage(
    manifest: dict[str, Any],
    output_files: Sequence[Path],
    *,
    complete_run: bool = False,
) -> None:
    """Record saved output paths and completion in the shared run record."""
    for path in output_files:
        logging.info("Wrote %s (%d bytes)", path, path.stat().st_size)
    manifest["outputs"] = [str(path) for path in output_files]
    manifest["status"] = "complete"
    manifest["completed_at_utc"] = datetime.now(timezone.utc).isoformat()
    run_path = Path("logs/run.json")
    run = json.loads(run_path.read_text())
    run["stages"][manifest["stage"]] = manifest
    if complete_run:
        run["status"] = "complete"
        run["completed_at_utc"] = manifest["completed_at_utc"]
    run_path.write_text(json.dumps(run, indent=2, allow_nan=False) + "\n")
    logging.info("Completed %s", manifest["stage"])
