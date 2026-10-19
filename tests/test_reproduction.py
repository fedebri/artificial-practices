"""Exercise the complete synthesized workflow using known synthetic data."""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pandas as pd
import pytest


@pytest.fixture
def frozen_project(project: Path) -> Path:
    """Supply two G20 countries with known native-schema distances."""
    repository = Path(__file__).resolve().parents[1]
    for folder in ("pipeline", "src"):
        shutil.copytree(repository / folder, project / folder)
    for relative in ("Makefile", "environment.yml"):
        shutil.copy2(repository / relative, project / relative)
    source_paths = sorted((project / "data/raw").rglob("aei*csv"))
    for path in source_paths:
        frame = pd.read_csv(path, dtype="string", keep_default_na=False)
        monthly = "metric_id" in frame
        frame["geo_id"] = frame["geo_id"].replace({"NA": "BR", "NAM": "BRA"})
        for index, row in frame.iterrows():
            geography = row["geo_level"] if monthly else row["geography"]
            if geography != "country":
                continue
            label = row["metric_id"] if monthly else row["cluster_name"]
            mode = label.removeprefix("collaboration_").removesuffix("_pct")
            mode = {
                "feedback loop": "feedback_loop",
                "task iteration": "task_iteration",
            }.get(mode, mode)
            if mode not in {
                "directive",
                "feedback_loop",
                "learning",
                "task_iteration",
                "validation",
            }:
                continue
            endpoint = row["date_start"] in {"2026-02-05", "2026-05-01"}
            target = (
                "learning"
                if endpoint or row["geo_id"] in {"BR", "BRA"}
                else "directive"
            )
            frame.loc[index, "value"] = "80" if mode == target else "0"
        if "release_2026_03_24" in str(path):
            none = frame.loc[frame["geo_id"].eq("BR")].copy()
            none["geo_id"] = "NONE"
            frame = pd.concat([frame, none], ignore_index=True)
        frame.to_csv(path, index=False)
    crosswalk = (
        project
        / "data/raw/release_2025_09_15/data/intermediate/iso_country_codes.csv"
    )
    pd.DataFrame(
        {
            "iso_alpha_2": ["BR", "US"],
            "iso_alpha_3": ["BRA", "USA"],
            "country_name": ["Brazil", "United States"],
        }
    ).to_csv(crosswalk, index=False)
    locked_paths = [
        *source_paths,
        crosswalk,
        *sorted((project / "data/raw").rglob("data_documentation.md")),
    ]
    lock = {
        str(path.relative_to(project)): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in locked_paths
    }
    (project / "docs/reproduction_sources.json").write_text(
        json.dumps({"sha256": lock})
    )
    return project


def test_raw_to_report_uses_one_curated_table(frozen_project: Path) -> None:
    for relative in (
        "archive",
        "data/interim",
        "data/processed",
        "results",
        "logs",
    ):
        assert not (frozen_project / relative).exists()
    execution = subprocess.run(
        ["make", "-j2", f"PYTHON={sys.executable}", "practices"],
        cwd=frozen_project,
        capture_output=True,
        text=True,
        timeout=180,
        env={
            **os.environ,
            "PYTHONPATH": str(frozen_project / "src"),
            "OPENBLAS_NUM_THREADS": "1",
            "OMP_NUM_THREADS": "1",
        },
    )
    assert execution.returncode == 0, execution.stdout + execution.stderr
    results = frozen_project / "results"
    assert not (results / "reproduction").exists()
    profile_dir = results / "02_build_profiles"
    assert sorted(path.name for path in profile_dir.glob("*.csv")) == [
        "profiles.csv"
    ]
    profiles = pd.read_csv(profile_dir / "profiles.csv")
    assert len(profiles) == 15
    assert not (profile_dir / "profiles.parquet").exists()
    key = [
        "source_id",
        "date_start",
        "date_end",
        "geo_level",
        "profile_geo_id",
    ]
    assert not profiles.duplicated(key).any()
    assert "sample_id" not in profiles
    assert profiles["in_full_published"].sum() == 10
    assert profiles["in_g20_common_five"].sum() == 10
    assert profiles["in_common_five"].sum() == 10
    assert profiles["in_legacy_stable"].sum() == 6
    assert profiles["in_monthly_stable"].sum() == 4
    assert len(profiles.loc[profiles["geo_level"].eq("global")]) == 5
    crosswalk = (
        "data/raw/release_2025_09_15/data/intermediate/iso_country_codes.csv"
    )
    run_log = json.loads((frozen_project / "logs/run.json").read_text())
    assert run_log["status"] == "complete"
    assert len(run_log["stages"]) == 7
    assert sorted(
        path.name for path in (frozen_project / "logs").iterdir()
    ) == ["practices.log", "run.json"]
    manifest = run_log["stages"]["02_build_profiles"]
    assert (
        manifest["crosswalk_sha256"]
        == hashlib.sha256(
            (frozen_project / crosswalk).read_bytes()
        ).hexdigest()
    )
    assert manifest["quarantined_records"] == 6
    assert not (frozen_project / "data/processed").exists()
    windows = pd.read_csv(results / "03_estimate/window_summary.csv")
    g20 = windows.loc[windows["sample_id"].eq("g20_common_five")].sort_values(
        "date_start"
    )
    assert g20["mean_js_distance"].tolist() == [1.0, 1.0, 0.0, 1.0, 0.0]
    contrasts = pd.read_csv(results / "04_sensitivity/contrasts.csv")
    cross = contrasts.loc[
        contrasts["contrast_id"].eq("august_may_cross_regime")
    ]
    assert cross["sample_id"].tolist() == ["g20_common_five"]
    assert cross["analysis_role"].tolist() == ["secondary_cross_regime"]
    assert cross["behavioral_change_identified"].tolist() == [False]
    assert cross["mean_js_distance_change"].tolist() == [-1.0]
    changes = pd.read_csv(results / "04_sensitivity/country_changes.csv")
    own = changes.loc[
        changes["contrast_id"].eq("august_may_cross_regime")
    ].set_index("country_iso3")
    assert own.loc["USA", "own_profile_js_distance"] == 1
    assert own.loc["BRA", "own_profile_js_distance"] == 0
    omissions = pd.read_csv(
        results / "04_sensitivity/mode_sensitivity_windows.csv"
    )
    assert "unavailable_zero_remaining_mass" in set(omissions["status"])
    model = pd.read_csv(results / "model_diagnostic/model_contrasts.csv")
    assert model["absolute_error"].lt(1e-10).all()
    consumer = pd.read_csv(results / "05_export/consumer_metrics.csv")
    for location in consumer["result_location"].dropna().unique():
        assert (results / "05_export" / location).is_file(), location
    assert consumer["uncertainty"].eq("not_estimated").all()
    assert (
        consumer.loc[consumer["table"].eq("g20_country_distances"), "note"]
        .isna()
        .all()
    )
    assert not (results / "05_export/tables").exists()
    assert not (results / "05_export/core_consumer_metrics.csv").exists()
    assert not (results / "05_export/model_observations.csv").exists()
    # The complete pipeline has 20 distinct data/result tables, with no audit
    # tables or core/G20 copies. Only pairs and the final consumer get Parquet,
    # retaining the minimum of 100 rows for these two exports.
    expected = {
        "01_load_audit": 0,
        "02_build_profiles": 1,
        "03_estimate": 4,
        "04_sensitivity": 8,
        "model_diagnostic": 5,
        "05_export": 1,
        "06_report": 0,
    }
    for name, csv_count in expected.items():
        stage = results / name
        assert len(list(stage.glob("*.csv"))) == csv_count
        assert not (stage / "provenance").exists()
        assert not (stage / "run_manifest.json").exists()
        assert not (stage / "stage.log").exists()
        record = run_log["stages"][name]
        assert record["status"] == "complete"
        assert record["seed"] is None
        assert "input_sha256" not in record
        assert "output_sha256" not in record
        assert "packages" not in record
        for filename in record["outputs"]:
            path = frozen_project / filename
            assert path.is_file()
            if path.suffix == ".parquet":
                assert path.stem in {"pairwise_distances", "consumer_metrics"}
                assert len(pd.read_parquet(path)) >= 100
    for path in [
        *results.rglob("*.csv"),
        *(frozen_project / "data/interim").rglob("*.csv"),
    ]:
        assert path.with_suffix(".parquet").exists() == (
            path.stem in {"pairwise_distances", "consumer_metrics"}
            and len(pd.read_csv(path)) >= 100
        )
    note_path = results / "06_report/research_note.md"
    assert "constant measurement" in note_path.read_text()
    for target in re.findall(
        r"!?\[[^\]]*\]\(([^)]+)\)", note_path.read_text()
    ):
        if "://" not in target:
            assert (note_path.parent / target).is_file(), target


@pytest.mark.parametrize("failure", ["hash", "missing", "lock_changed"])
def test_original_crosswalk_integrity_at_profile_construction(
    frozen_project: Path,
    failure: str,
) -> None:
    """Reject missing/changed raw mappings and a replaced audited source lock."""
    crosswalk = frozen_project / (
        "data/raw/release_2025_09_15/data/intermediate/iso_country_codes.csv"
    )
    if failure == "missing":
        # Loading the published collaboration cells does not need this file.
        crosswalk.rename(crosswalk.with_suffix(".unavailable"))
    loading = subprocess.run(
        ["make", f"PYTHON={sys.executable}", "practices-load"],
        cwd=frozen_project,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert loading.returncode == 0, loading.stdout + loading.stderr
    if failure != "missing":
        frame = pd.read_csv(crosswalk, dtype="string", keep_default_na=False)
        frame.loc[0, "country_name"] = "Changed after loading"
        frame.to_csv(crosswalk, index=False)
        if failure == "lock_changed":
            lock_path = frozen_project / "docs/reproduction_sources.json"
            lock = json.loads(lock_path.read_text())
            lock["sha256"][str(crosswalk.relative_to(frozen_project))] = (
                hashlib.sha256(crosswalk.read_bytes()).hexdigest()
            )
            lock_path.write_text(json.dumps(lock))
    construction = subprocess.run(
        [sys.executable, "pipeline/02_build_profiles.py"],
        cwd=frozen_project,
        env={**os.environ, "PYTHONPATH": str(frozen_project / "src")},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert construction.returncode != 0
    expected = {
        "hash": "iso_country_codes.csv: differs from the frozen source SHA-256",
        "missing": "No such file or directory",
        "lock_changed": "reproduction_sources.json: differs from",
    }[failure]
    assert expected in construction.stderr
    assert (
        json.loads((frozen_project / "logs/run.json").read_text())["stages"][
            "02_build_profiles"
        ]["status"]
        == "incomplete"
    )
    assert not (
        frozen_project / "results/02_build_profiles/profiles.csv"
    ).exists()


@pytest.mark.parametrize(
    "failure",
    ["source_audit", "geography_audit", "missing_native"],
)
def test_profile_stage_requires_completed_load_and_its_input_file(
    frozen_project: Path,
    failure: str,
) -> None:
    """Failed audits block construction; missing CSVs fail on their normal read."""
    failed_audit = failure in {"source_audit", "geography_audit"}
    if failed_audit:
        path = next(
            (frozen_project / "data/raw/release_2025_09_15").rglob("aei*csv")
        )
        frame = pd.read_csv(path, dtype="string", keep_default_na=False)
        if failure == "source_audit":
            frame.loc[0, "value"] = "101"
        else:
            frame.loc[0, "geo_id"] = "UNASSIGNED"
        frame.to_csv(path, index=False)
        lock_path = frozen_project / "docs/reproduction_sources.json"
        lock = json.loads(lock_path.read_text())
        lock["sha256"][str(path.relative_to(frozen_project))] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        lock_path.write_text(json.dumps(lock))
    loading = subprocess.run(
        ["make", f"PYTHON={sys.executable}", "practices-load"],
        cwd=frozen_project,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if failed_audit:
        assert loading.returncode != 0
        assert "unaccepted source audit flags" in loading.stderr
        expected_error = "upstream stage is not complete"
    else:
        assert loading.returncode == 0, loading.stdout + loading.stderr
        relative = "data/interim/reproduction/native_collaboration.csv"
        path = frozen_project / relative
        path.rename(path.with_suffix(".unavailable"))
        expected_error = "No such file or directory"
    construction = subprocess.run(
        [sys.executable, "pipeline/02_build_profiles.py"],
        cwd=frozen_project,
        env={**os.environ, "PYTHONPATH": str(frozen_project / "src")},
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert construction.returncode != 0
    assert expected_error in construction.stderr
    run_log = json.loads((frozen_project / "logs/run.json").read_text())
    assert run_log["stages"]["02_build_profiles"]["status"] == "incomplete"
    assert not (
        frozen_project / "results/02_build_profiles/profiles.csv"
    ).exists()


@pytest.mark.parametrize(
    "failure",
    ["hash", "percentage", "unknown_country", "identifier_collision"],
)
def test_frozen_source_and_mapping_failures_are_visible(
    frozen_project: Path,
    failure: str,
) -> None:
    path = next(
        (frozen_project / "data/raw/release_2025_09_15").rglob("aei*csv")
    )
    frame = pd.read_csv(path, dtype="string", keep_default_na=False)
    if failure == "identifier_collision":
        alias = frame.loc[frame["geo_id"].eq("BR")].copy()
        alias["geo_id"] = "BRA"
        frame = pd.concat([frame, alias], ignore_index=True)
    elif failure == "unknown_country":
        frame.loc[frame["geo_id"].eq("BR"), "geo_id"] = "ZZ"
    else:
        frame.loc[0, "value"] = "101"
    frame.to_csv(path, index=False)
    if failure != "hash":
        lock_path = frozen_project / "docs/reproduction_sources.json"
        lock = json.loads(lock_path.read_text())
        lock["sha256"][str(path.relative_to(frozen_project))] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        lock_path.write_text(json.dumps(lock))
    execution = subprocess.run(
        ["make", f"PYTHON={sys.executable}", "practices-profiles"],
        cwd=frozen_project,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert execution.returncode != 0
    expected = {
        "hash": "frozen source SHA-256",
        "percentage": "unaccepted source audit flags",
        "unknown_country": "unresolved country mapping flags",
        "identifier_collision": "unresolved country mapping flags",
    }[failure]
    assert expected in execution.stderr
    assert not (
        frozen_project / "results/02_build_profiles/profiles.csv"
    ).exists()


def test_missing_mode_is_excluded_without_imputation(
    frozen_project: Path,
) -> None:
    path = next(
        (frozen_project / "data/raw/release_2025_09_15").rglob("aei*csv")
    )
    frame = pd.read_csv(path, dtype="string", keep_default_na=False)
    frame = frame.loc[
        ~(frame["geo_id"].eq("BR") & frame["cluster_name"].eq("validation"))
    ]
    frame.to_csv(path, index=False)
    lock_path = frozen_project / "docs/reproduction_sources.json"
    lock = json.loads(lock_path.read_text())
    lock["sha256"][str(path.relative_to(frozen_project))] = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()
    lock_path.write_text(json.dumps(lock))
    execution = subprocess.run(
        ["make", f"PYTHON={sys.executable}", "practices-profiles"],
        cwd=frozen_project,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert execution.returncode == 0, execution.stdout + execution.stderr
    profiles = pd.read_csv(
        frozen_project / "results/02_build_profiles/profiles.csv"
    )
    assert set(
        profiles.loc[profiles["in_g20_common_five"], "country_iso3"]
    ) == {"USA"}
    incomplete = profiles.loc[
        profiles["country_iso3"].eq("BRA")
        & profiles["date_start"].eq("2025-08-04")
    ].iloc[0]
    assert pd.isna(incomplete["published_validation_pct"])
    assert pd.isna(incomplete["conditional_directive_share"])
    assert not incomplete["partition_eligible"]
    assert profiles["in_full_published"].sum() == 9


@pytest.mark.parametrize("sequence", ["legacy", "monthly"])
def test_membership_preserves_sequence_scope(
    frozen_project: Path, sequence: str
) -> None:
    lock_path = frozen_project / "docs/reproduction_sources.json"
    lock = json.loads(lock_path.read_text())
    for path in (frozen_project / "data/raw").rglob("aei*csv"):
        frame = pd.read_csv(path, dtype="string", keep_default_na=False)
        monthly = "metric_id" in frame
        if monthly == (sequence == "monthly"):
            continue
        frame = frame.loc[~frame["geo_id"].isin(["BR", "BRA"])]
        frame.to_csv(path, index=False)
        lock["sha256"][str(path.relative_to(frozen_project))] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
    lock_path.write_text(json.dumps(lock))
    execution = subprocess.run(
        ["make", f"PYTHON={sys.executable}", "practices-profiles"],
        cwd=frozen_project,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert execution.returncode == 0, execution.stdout + execution.stderr
    profiles = pd.read_csv(
        frozen_project / "results/02_build_profiles/profiles.csv"
    )
    brazil = profiles.loc[profiles["country_iso3"].eq("BRA")]
    assert len(brazil) == (3 if sequence == "legacy" else 2)
    assert brazil[f"in_{sequence}_stable"].all()
    assert not brazil["in_common_five"].any()
    assert not brazil["in_g20_common_five"].any()
    manifest = json.loads((frozen_project / "logs/run.json").read_text())[
        "stages"
    ]["02_build_profiles"]
    assert {"CHN", "IND"} <= set(manifest["unpublished_g20_countries"])
