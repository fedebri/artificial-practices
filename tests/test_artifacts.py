"""Check shared run logging and CSV export at real file boundaries."""

import hashlib
import json
from pathlib import Path
import sys

import pandas as pd
import pytest

from artifacts import (
    begin_stage,
    finish_stage,
    write_tables,
)


@pytest.fixture
def workspace(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Supply a tiny environment for a new run, without empirical inputs."""
    (tmp_path / "stage.py").write_text('"""Synthetic stage."""\n')
    (tmp_path / "environment.yml").write_text("name: synthetic\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["stage.py"])
    return tmp_path


@pytest.mark.parametrize("absolute_script", [False, True])
@pytest.mark.parametrize("rows", [0, 2, 99, 100, 101])
def test_completed_manifest_records_only_actual_formats(
    workspace: Path,
    monkeypatch: pytest.MonkeyPatch,
    absolute_script: bool,
    rows: int,
) -> None:
    if absolute_script:
        monkeypatch.setattr(sys, "argv", [str(workspace / "stage.py")])
    result_dir = Path("results/producer")
    manifest = begin_stage(result_dir, (), None, new_run=True)
    data = pd.DataFrame({"value": pd.Series(range(rows), dtype="float64")})
    if rows:
        data.loc[rows - 1, "value"] = None
    outputs = write_tables({"values": data}, result_dir)
    assert outputs[0] == result_dir / "values.csv"
    assert not (result_dir / "values.parquet").exists()
    assert len(outputs) == 1
    finish_stage(manifest, outputs, complete_run=True)
    run = json.loads(Path("logs/run.json").read_text())
    completed = run["stages"]["producer"]
    assert run["status"] == "complete"
    assert completed["status"] == "complete"
    assert completed["outputs"] == [str(path) for path in outputs]
    assert completed["command"] == sys.argv
    assert "packages" in run and "packages" not in completed
    assert (
        run["environment_sha256"]
        == hashlib.sha256(
            (workspace / "environment.yml").read_bytes()
        ).hexdigest()
    )
    assert "output_sha256" not in completed
    assert sorted(path.name for path in result_dir.iterdir()) == ["values.csv"]
    assert sorted(path.name for path in Path("logs").iterdir()) == [
        "practices.log",
        "run.json",
    ]
    saved = pd.read_csv(outputs[0])
    pd.testing.assert_frame_equal(saved, data, check_dtype=rows > 0)


def test_csv_preserves_identifiers_empty_strings_and_missing_values(
    workspace: Path,
) -> None:
    """A CSV-only table must distinguish Namibia, an empty note and a null."""
    data = pd.DataFrame(
        {
            "country": ["NA", "US", "BR"],
            "note": ["", None, "published"],
            "value": [0.12345678901234566, None, 0.0],
        }
    )
    outputs = write_tables({"values": data}, Path("results/io"))
    assert len(outputs) == 1
    saved = pd.read_csv(
        outputs[0],
        keep_default_na=False,
        na_values=["<NA>"],
        float_precision="round_trip",
    )
    assert saved["country"].tolist() == ["NA", "US", "BR"]
    assert saved.loc[0, "note"] == ""
    assert pd.isna(saved.loc[1, "note"])
    assert pd.isna(saved.loc[1, "value"])
    assert saved.loc[0, "value"] == data.loc[0, "value"]
    assert saved.loc[2, "value"] == 0.0


def test_completed_upstream_does_not_require_intermediate_hashes(
    workspace: Path,
) -> None:
    producer = Path("results/producer")
    manifest = begin_stage(producer, (), None, new_run=True)
    output = producer / "value.txt"
    output.write_text("original")
    finish_stage(manifest, (output,))
    output.write_text("changed")
    consumer = Path("results/consumer")
    record = begin_stage(consumer, (output,), None, ("producer",))
    assert record["inputs"] == [str(output)]
    assert record["status"] == "incomplete"
    assert "input_sha256" not in record
    assert "code_and_document_sha256" not in record
    assert (
        "[producer] Completed producer"
        in Path("logs/practices.log").read_text()
    )
    assert "[consumer] Reading" in Path("logs/practices.log").read_text()


def test_new_run_resets_the_previous_run_log(workspace: Path) -> None:
    begin_stage(Path("results/old"), (), None, new_run=True)
    begin_stage(Path("results/new"), (), None, new_run=True)
    run = json.loads(Path("logs/run.json").read_text())
    assert set(run["stages"]) == {"new"}
    assert "[old]" not in Path("logs/practices.log").read_text()


def test_missing_output_leaves_the_stage_incomplete(workspace: Path) -> None:
    manifest = begin_stage(Path("results/producer"), (), None, new_run=True)
    with pytest.raises(FileNotFoundError, match="missing.png"):
        finish_stage(manifest, (Path("missing.png"),))
    assert (
        json.loads(Path("logs/run.json").read_text())["stages"]["producer"][
            "status"
        ]
        == "incomplete"
    )


def test_incomplete_upstream_is_rejected(workspace: Path) -> None:
    producer = Path("results/producer")
    begin_stage(producer, (), None, new_run=True)
    with pytest.raises(ValueError, match="not complete"):
        begin_stage(
            Path("results/consumer"),
            (),
            None,
            ("producer",),
        )


def test_input_read_failure_leaves_the_stage_incomplete(
    workspace: Path,
) -> None:
    result_dir = Path("results/producer")
    missing = Path("missing.csv")
    begin_stage(result_dir, (missing,), None, new_run=True)
    with pytest.raises(FileNotFoundError, match="missing.csv"):
        missing.read_text()
    assert (
        json.loads(Path("logs/run.json").read_text())["stages"]["producer"][
            "status"
        ]
        == "incomplete"
    )
