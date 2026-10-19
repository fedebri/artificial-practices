"""Compare the synthesized workflow with locked historical science tables.

This optional local check requires the ignored accepted reference bundles.
It is separate from make practices, which needs only the locked raw inputs.
The JSON inventory maps reorganized artifact paths, not analytical rules.
Execution/provenance fields may change; scientific columns, memberships,
roles, statuses and nulls must match at the original numerical tolerances.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


INPUT_REFERENCE_LOCK = Path("docs/reproduction_reference.json")
INPUT_CONTRASTS = Path("results/04_sensitivity/contrasts.csv")
INPUT_RUN_LOG = Path("logs/run.json")
INPUT_REFERENCE_METADATA = Path(
    "archive/inspection_workflow_2026_10_16/results/06_evaluate_export/"
    "20261015T184715523168Z/consumer_metadata.json"
)
OUTPUT_VERIFICATION = Path("logs/verification.json")
SEED = None  # Deterministic comparison.

lock = json.loads(INPUT_REFERENCE_LOCK.read_text())
record = {
    "status": "incomplete",
    "started_at_utc": datetime.now(timezone.utc).isoformat(),
    "reference_lock": str(INPUT_REFERENCE_LOCK),
    "seed": SEED,
    "atol": 1e-12,
    "rtol": 1e-10,
    "tables": [],
}
OUTPUT_VERIFICATION.parent.mkdir(parents=True, exist_ok=True)
OUTPUT_VERIFICATION.write_text(json.dumps(record, indent=2) + "\n")
run = json.loads(INPUT_RUN_LOG.read_text())
source = run["stages"]["01_load_audit"]
export = run["stages"]["05_export"]
reference_metadata = json.loads(INPUT_REFERENCE_METADATA.read_text())
if source["status"] != "complete" or export["status"] != "complete":
    raise ValueError("Complete the source-to-export build before comparison")
for packages in reference_metadata["producer_packages"].values():
    for package, expected in packages.items():
        if run["packages"][package] != expected:
            raise ValueError(
                f"{package}: differs from the reference version {expected}"
            )
if run["environment_sha256"] != reference_metadata["environment_sha256"]:
    raise ValueError("environment.yml differs from the accepted replay")
for expected in reference_metadata["source_fingerprints"]:
    actual = next(
        row
        for row in source["source_fingerprints"]
        if row["source_id"] == expected["source_id"]
    )
    for field in ("relative_path", "sha256", "documentation_sha256"):
        if actual[field] != expected[field]:
            raise ValueError(
                f"{expected['source_id']}: source {field} differs"
            )

contrasts = pd.read_csv(
    INPUT_CONTRASTS,
    keep_default_na=False,
    na_values=["<NA>"],
    float_precision="round_trip",
)
cross_scope = contrasts.loc[
    contrasts["contrast_id"].eq("august_may_cross_regime")
].iloc[0]
for item in lock["tables"]:
    reference_path = Path(item["reference"])
    candidate_path = Path(item["candidate"])
    with reference_path.open("rb") as handle:
        reference_hash = hashlib.file_digest(handle, "sha256").hexdigest()
    if reference_hash != item["sha256"]:
        raise ValueError(
            f"{reference_path}: reference differs from its locked hash"
        )
    with candidate_path.open("rb") as handle:
        candidate_hash = hashlib.file_digest(handle, "sha256").hexdigest()
    reference = pd.read_parquet(reference_path)
    candidate = pd.read_csv(
        candidate_path,
        keep_default_na=False,
        na_values=["<NA>"],
        float_precision="round_trip",
        dtype={
            "published_value": "string",
            "source_hierarchy_level": "string",
        },
    )
    # Historical bundles stored overlapping samples separately. Reconstruct
    # those comparison views in memory from the single flagged profile table.
    if "expand_samples" in item:
        candidate = pd.concat(
            [
                candidate.loc[candidate[f"in_{sample}"]].assign(
                    sample_id=sample, design_id="convergence_v1"
                )
                for sample in item["expand_samples"]
            ],
            ignore_index=True,
        )
        candidate["country_label"] = candidate["country_name"]
    if item.get("profile_view") == "published_global":
        candidate = candidate.loc[candidate["geo_level"].eq("global")].assign(
            sample_id="published_global"
        )
    elif item.get("profile_view") == "g20_common_five":
        candidate = candidate.loc[candidate["in_g20_common_five"]].assign(
            sample_id="g20_common_five",
            source_sample_id="full_published",
            design_id="g20_profiles_v1",
        )
    if item.get("core_consumer"):
        candidate = candidate.loc[candidate["design_id"].eq("convergence_v1")]

    if item.get("sample"):
        candidate = candidate.loc[candidate["sample_id"].eq(item["sample"])]
    if item.get("exclude_sample"):
        candidate = candidate.loc[
            candidate["sample_id"].ne(item["exclude_sample"])
        ]
    if item.get("exclude_contrast"):
        candidate = candidate.loc[
            candidate["contrast_id"].ne(item["exclude_contrast"])
        ]
    if item.get("contrast"):
        candidate = candidate.loc[
            candidate["contrast_id"].eq(item["contrast"])
        ]
    if item.get("dates"):
        candidate = candidate.loc[candidate["date_start"].isin(item["dates"])]
    if item.get("cross_scope"):
        # Window/mode levels are computed once and reused by the
        # endpoint comparison. Qualifiers come from the actual new
        # cross-regime contrast, rather than being synthesized from the
        # reference.
        for field in (
            "design_id",
            "analysis_role",
            "comparison_id",
            "estimand",
            "measurement_equivalence",
            "behavioral_change_identified",
        ):
            candidate = candidate.assign(**{field: cross_scope[field]})
    if item.get("rename"):
        candidate = candidate.rename(columns=item["rename"])
    columns = [
        name
        for name in reference.columns
        if not (
            name == "run_id"
            or name.endswith("_run_id")
            or name in ("source_stage", "result_location")
        )
    ]
    pd.testing.assert_frame_equal(
        reference[columns]
        .astype(object)
        .where(reference[columns].notna(), None)
        .sort_values(columns)
        .reset_index(drop=True),
        candidate[columns]
        .astype(object)
        .where(candidate[columns].notna(), None)
        .sort_values(columns)
        .reset_index(drop=True),
        check_dtype=False,
        check_exact=False,
        atol=1e-12,
        rtol=1e-10,
        obj=str(reference_path),
    )
    record["tables"].append(
        {
            "reference": str(reference_path),
            "candidate": str(candidate_path),
            "reference_sha256": reference_hash,
            "candidate_sha256": candidate_hash,
            "rows": len(reference),
            "scientific_columns": columns,
        }
    )
    print(f"Matched {reference_path}: {len(reference):,} rows")

# The unified consumer preserves the original core fields without a copy.
reference_schema = pq.read_schema(
    (
        "archive/inspection_workflow_2026_10_16/results/06_evaluate_export/"
        "20261015T184715523168Z/consumer_metrics.parquet"
    )
).remove_metadata()
candidate_schema = pq.read_schema(
    "results/05_export/consumer_metrics.parquet"
).remove_metadata()
assert all(
    candidate_schema.field(field.name) == field for field in reference_schema
), "Core consumer schema changed"
record.update(
    {
        "status": "matched_reference",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_run_id": source["run_id"],
        "export_run_id": export["run_id"],
        "matched_tables": len(record["tables"]),
        "core_consumer_schema": "unchanged",
        "historical_release_status": (
            "unchanged; no release is published by this check"
        ),
    }
)
OUTPUT_VERIFICATION.write_text(json.dumps(record, indent=2) + "\n")
print(
    f"Matched {record['matched_tables']} reference tables; "
    f"record: {OUTPUT_VERIFICATION}"
)
