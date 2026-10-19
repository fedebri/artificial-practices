"""Extract and audit the original Anthropic collaboration aggregates.

Verify four source CSVs and their dictionaries against the frozen source lock.
Select country/global overall collaboration percentages, harmonize legacy and
monthly column names and labels, and retain original values and source records.
The facet/category filters prevent pooling percentages with different denominators.

Check keys, percentages, measures, windows, IDs and five-mode coverage. Missing
modes remain missing. The accepted February NONE records stay in the native
table and audit log; any unaccepted source issue stops completion.

Write one native_collaboration.csv under data/interim/reproduction.
Coverage flags travel with those same records.
Audit findings, source windows, filter counts and fingerprints belong in
logs/practices.log and logs/run.json.
Country reconciliation and analytical sample flags are constructed in Stage 2.
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

# Track file integrity (hashlib)
# and record execution steps and audit findings (logging).
# The shared artifact helpers record the run environment and stage status.
import hashlib
import logging

from artifacts import (
    begin_stage,
    finish_stage,
    write_tables,
)


INPUT_FILES = (
    Path(
        "data/raw/release_2025_09_15/data/intermediate/"
        "aei_raw_claude_ai_2025-08-04_to_2025-08-11.csv"
    ),
    Path(
        "data/raw/release_2026_01_15/data/intermediate/"
        "aei_raw_claude_ai_2025-11-13_to_2025-11-20.csv"
    ),
    Path(
        "data/raw/release_2026_03_24/data/"
        "aei_raw_claude_ai_2026-02-05_to_2026-02-12.csv"
    ),
    Path("data/raw/release_2026_06_26/data/" "aei_claude_ai_2026-06-26.csv"),
)
DOCUMENTATION_FILES = (
    Path("data/raw/release_2025_09_15/data_documentation.md"),
    Path("data/raw/release_2026_01_15/data_documentation.md"),
    Path("data/raw/release_2026_03_24/data_documentation.md"),
    Path("data/raw/release_2026_06_26/data_documentation.md"),
)

# Expected source-file SHA-256 hashes; stop if local inputs differ.
INPUT_SOURCE_LOCK = Path("docs/reproduction_sources.json")
OUTPUT_NATIVE = Path("data/interim/reproduction/native_collaboration.csv")
RESULTS_DIR = Path("results/01_load_audit")

manifest = begin_stage(
    RESULTS_DIR,
    (*INPUT_FILES, *DOCUMENTATION_FILES, INPUT_SOURCE_LOCK),
    seed=None,
    new_run=True,
)
run_id = manifest["run_id"]
# Check source data sha256
source_lock = json.loads(INPUT_SOURCE_LOCK.read_text())["sha256"]
with INPUT_SOURCE_LOCK.open("rb") as handle:
    manifest["source_lock_sha256"] = hashlib.file_digest(
        handle, "sha256"
    ).hexdigest()

# Process each release alongside its documentation using the appropriate schema.
# Collect selected collaboration rows, source-file metadata and row-selection counts.
# release data
selected_chunks = []
# source metadata
inventory_rows = []
# records how many rows remain after each selection
flow_rows = []

for input_path, documentation_path, schema in zip(
    INPUT_FILES,
    DOCUMENTATION_FILES,
    ("legacy", "legacy", "legacy", "monthly"),
    strict=True,
):
    # Logging release after extract
    source_id = input_path.relative_to("data/raw").parts[0]
    logging.info("Reading %s (%s)", input_path, schema)
    # Retrieve Statistics
    stat = input_path.stat()
    with input_path.open("rb") as handle:
        input_digest = hashlib.file_digest(handle, "sha256").hexdigest()
    with documentation_path.open("rb") as handle:
        documentation_digest = hashlib.file_digest(
            handle, "sha256"
        ).hexdigest()
    for path, digest in (
        (input_path, input_digest),
        (documentation_path, documentation_digest),
    ):
        if digest != source_lock[str(path)]:
            raise ValueError(f"{path}: differs from the frozen source SHA-256")
    # Inspect header and parse column names
    header = pd.read_csv(input_path, nrows=0).columns.tolist()
    if schema == "legacy":
        columns = [
            "date_start",
            "date_end",
            "geo_id",
            "value",
            "geography",
            "facet",
            "level",
            "variable",
            "cluster_name",
            "platform_and_product",
        ]
    else:
        columns = [
            "date_start",
            "date_end",
            "geo_id",
            "value",
            "geo_level",
            "category_name",
            "hierarchy_level",
            "metric_id",
            "node_name",
        ]
    # Chunking bounds memory use without aggregating or weighting observations.
    # Counts at each filter expose exactly which published rows were excluded.
    scanned = geographic = category = selected_count = 0
    country_rows = global_rows = 0
    for chunk in pd.read_csv(
        input_path,
        usecols=columns,
        dtype="string",
        keep_default_na=False,  # NA is Namibia, not a missing country ID.
        chunksize=200_000,
    ):
        scanned += len(chunk)
        if schema == "legacy":
            # Use overall collaboration, not collaboration within
            # individual tasks or requests, whose percentages have
            # different denominators.
            frame = chunk.loc[chunk["geography"].isin(["country", "global"])]
            geographic += len(frame)
            frame = frame.loc[frame["facet"].eq("collaboration")]
            category += len(frame)
            frame = frame.loc[frame["variable"].eq("collaboration_pct")].copy()
            frame = frame.rename(
                columns={
                    "geography": "geo_level",
                    "variable": "source_metric",
                    "cluster_name": "source_label",
                    "level": "source_hierarchy_level",
                    "platform_and_product": "source_product",
                    "value": "published_value",
                }
            ).drop(columns="facet")
            # Legacy labels use spaces; monthly metric IDs use
            # underscores. Preserve the native label and map only these observed aliases.
            frame["measure"] = frame["source_label"].replace(
                {
                    "feedback loop": "feedback_loop",
                    "task iteration": "task_iteration",
                }
            )
        else:
            # "overall" is the monthly counterpart of the legacy facet.
            # GLOBAL is retained as context; subregions never enter the sample.
            frame = chunk.loc[chunk["geo_level"].isin(["country", "global"])]
            geographic += len(frame)
            frame = frame.loc[frame["category_name"].eq("overall")]
            category += len(frame)
            # Keep buckets and unknown collaboration labels for source review.
            frame = frame.loc[
                frame["metric_id"].str.startswith("collaboration_")
                & frame["metric_id"].str.endswith("_pct")
            ].copy()
            frame = frame.rename(
                columns={
                    "metric_id": "source_metric",
                    "node_name": "source_label",
                    "hierarchy_level": "source_hierarchy_level",
                    "value": "published_value",
                }
            ).drop(columns="category_name")
            frame["measure"] = (
                frame["source_metric"]
                .str.removeprefix("collaboration_")
                .str.removesuffix("_pct")
            )
            frame["source_product"] = ""  # Absent from the monthly schema.
        frame["source_id"] = source_id
        frame["source_schema"] = schema
        # Logical CSV data-record number, not a physical line number.
        frame["source_record"] = frame.index + 1
        selected_count += len(frame)
        country_rows += int(frame["geo_level"].eq("country").sum())
        global_rows += int(frame["geo_level"].eq("global").sum())
        selected_chunks.append(frame)
    inventory_rows.append(
        {
            "source_id": source_id,
            "source_schema": schema,
            "relative_path": str(input_path),
            "documentation_path": str(documentation_path),
            "size_bytes": stat.st_size,
            "mtime_ns": stat.st_mtime_ns,
            "sha256": input_digest,
            "documentation_sha256": documentation_digest,
            "columns_in_file": json.dumps(header),
            "raw_rows_scanned": scanned,
            "selected_country_rows": country_rows,
            "selected_global_rows": global_rows,
        }
    )
    for step, rows_in, rows_out in (
        ("read_csv", scanned, scanned),
        ("country_or_global", scanned, geographic),
        ("collaboration_category", geographic, category),
        ("collaboration_percentage", category, selected_count),
    ):
        flow_rows.append(
            {
                "source_id": source_id,
                "step": step,
                "rows_in": rows_in,
                "rows_out": rows_out,
                "rows_excluded": rows_in - rows_out,
            }
        )
        logging.info("%s | %s: %d -> %d", source_id, step, rows_in, rows_out)


## Data quality audit
# Preserve published text alongside its numeric interpretation.
# Coercion makes malformed values visible in invalid_percentages instead of repairing them.
records = pd.concat(selected_chunks, ignore_index=True)
records["published_pct"] = pd.to_numeric(
    records["published_value"], errors="coerce"
).astype("float64")
source_inventory = pd.DataFrame(inventory_rows)

# Native-key and boundary audits; no duplicate removal or value correction.
geography_key = [
    "source_id",
    "date_start",
    "date_end",
    "geo_level",
    "geo_id",
]
# A geography/window/mode must identify one cell. Both copies of a
# duplicate are flagged, including aliases that map to the same canonical measure.
duplicate = records.duplicated(geography_key + ["measure"], keep=False)
invalid_pct = ~np.isfinite(records["published_pct"]) | ~records[
    "published_pct"
].between(0, 100)
unexpected_measure = ~records["measure"].isin(
    [
        "directive",
        "feedback_loop",
        "learning",
        "task_iteration",
        "validation",
        "none",
        "not_classified",
        "bucket_automation",
        "bucket_augmentation",
    ]
)
# This checks format only. Stage 2 also checks the supplied country crosswalk.
# An identifier with the right number of letters is not necessarily a country.
invalid_geo = (
    records["geo_level"].eq("country")
    & ~records["geo_id"].str.fullmatch(r"[A-Z]{2,3}")
) | (records["geo_level"].eq("global") & records["geo_id"].ne("GLOBAL"))

# June end dates are exclusive; legacy inclusivity is not established here.
source_contract = pd.DataFrame(
    [
        (
            "release_2025_09_15",
            "2025-08-04",
            "2025-08-11",
            "legacy",
            "unspecified",
        ),
        (
            "release_2026_01_15",
            "2025-11-13",
            "2025-11-20",
            "legacy",
            "unspecified",
        ),
        (
            "release_2026_03_24",
            "2026-02-05",
            "2026-02-12",
            "legacy",
            "unspecified",
        ),
        (
            "release_2026_06_26",
            "2026-04-01",
            "2026-05-01",
            "monthly",
            "exclusive",
        ),
        (
            "release_2026_06_26",
            "2026-05-01",
            "2026-06-01",
            "monthly",
            "exclusive",
        ),
    ],
    columns=[
        "source_id",
        "date_start",
        "date_end",
        "measurement_era",
        "end_date_convention",
    ],
)
window_key = ["source_id", "date_start", "date_end"]
# Require country and global availability for every expected source window.
window_check = records.merge(
    source_contract[window_key],
    on=window_key,
    how="left",
    indicator=True,
    validate="many_to_one",
)
period_key = ["source_id", "date_start", "date_end", "geo_level"]
required_windows = source_contract[window_key].merge(
    pd.DataFrame({"geo_level": ["country", "global"]}), how="cross"
)
window_presence = required_windows.merge(
    records[period_key].drop_duplicates(),
    on=period_key,
    how="left",
    indicator=True,
    validate="one_to_one",
)
tables = {
    "source_contract": source_contract,
    "source_inventory": source_inventory,
    "source_filter_counts": pd.DataFrame(flow_rows),
    "duplicate_keys": records.loc[duplicate].copy(),
    "invalid_percentages": records.loc[invalid_pct].copy(),
    "unexpected_measures": records.loc[unexpected_measure].copy(),
    "unexpected_windows": window_check.loc[
        window_check["_merge"].eq("left_only")
    ].drop(columns="_merge"),
    "missing_windows": window_presence.loc[
        window_presence["_merge"].eq("left_only"), period_key
    ].copy(),
    "invalid_geo_ids": records.loc[invalid_geo].copy(),
    "empty_sources": source_inventory.loc[
        source_inventory["selected_country_rows"].eq(0)
        | source_inventory["selected_global_rows"].eq(0)
    ].copy(),
}

# Publication completeness is a diagnostic, not an analytical sample rule.
# An absent mode can reflect publication thresholds and is never filled as zero.
coverage = (
    records.groupby(geography_key, dropna=False)
    .size()
    .to_frame("published_records")
)
mode_rows = records.loc[
    records["measure"].isin(
        [
            "directive",
            "feedback_loop",
            "learning",
            "task_iteration",
            "validation",
        ]
    )
].copy()
mode_rows["valid_pct"] = np.isfinite(mode_rows["published_pct"]) & mode_rows[
    "published_pct"
].between(0, 100)
mode_groups = mode_rows.groupby(geography_key, dropna=False)
mode_stats = mode_groups.agg(
    mode_records=("measure", "size"),
    distinct_modes=("measure", "nunique"),
    valid_mode_percentages=("valid_pct", "all"),
)
mode_stats["observed_five_mode_sum_pct"] = mode_groups["published_pct"].sum(
    min_count=5
)
coverage = coverage.join(mode_stats)
# These zeros count published records; no missing percentages are imputed.
coverage[["mode_records", "distinct_modes"]] = (
    coverage[["mode_records", "distinct_modes"]].fillna(0).astype(int)
)
coverage["all_five_modes_published"] = coverage["distinct_modes"].eq(5)
coverage["unique_valid_five_modes"] = (
    coverage["all_five_modes_published"]
    & coverage["mode_records"].eq(5)
    & coverage["valid_mode_percentages"].eq(True)
)
coverage["observed_five_mode_sum_pct"] = coverage[
    "observed_five_mode_sum_pct"
].where(coverage["unique_valid_five_modes"])
# Allow rounding of five percentages, while rejecting zero denominators.
# Totals below 100 are legitimate because none/unclassified mass lies outside these five modes.
# The 0.05-pp margin is rounding tolerance, not a coverage rule.
valid_total = coverage["observed_five_mode_sum_pct"].between(
    0, 100.05, inclusive="right"
)
coverage["candidate_complete_partition"] = (
    coverage["unique_valid_five_modes"] & valid_total
)
coverage = coverage.reset_index()
tables["geography_coverage"] = coverage
tables["invalid_partition_totals"] = coverage.loc[
    coverage["unique_valid_five_modes"]
    & ~coverage["candidate_complete_partition"]
].copy()
tables["coverage_summary"] = coverage.groupby(
    period_key, as_index=False, dropna=False
).agg(
    published_geographies=("geo_id", "size"),
    all_five_modes_published=("all_five_modes_published", "sum"),
    candidate_complete_partitions=("candidate_complete_partition", "sum"),
)
tables["percentage_summary"] = records.groupby(
    period_key + ["measure"], as_index=False, dropna=False
).agg(
    published_records=("published_value", "size"),
    numeric_values=("published_pct", "count"),
    min_pct=("published_pct", "min"),
    median_pct=("published_pct", "median"),
    max_pct=("published_pct", "max"),
)
tables["denominator_summary"] = (
    coverage.loc[coverage["unique_valid_five_modes"]]
    .groupby(period_key, as_index=False, dropna=False)
    .agg(
        complete_unique_partitions=("geo_id", "size"),
        min_five_mode_total_pct=("observed_five_mode_sum_pct", "min"),
        median_five_mode_total_pct=("observed_five_mode_sum_pct", "median"),
        max_five_mode_total_pct=("observed_five_mode_sum_pct", "max"),
    )
)
# These checks establish structural usability, not stable measurement across releases.
# Product eligibility and classifier definitions may still change.
review_names = (
    "duplicate_keys",
    "invalid_percentages",
    "unexpected_measures",
    "unexpected_windows",
    "missing_windows",
    "invalid_geo_ids",
    "invalid_partition_totals",
    "empty_sources",
)
review_counts = pd.DataFrame(
    [
        {"check": name, "flagged_rows": len(tables[name])}
        for name in review_names
    ]
)
review_counts["status"] = (
    review_counts["flagged_rows"]
    .gt(0)
    .map(
        {
            True: "review_required",
            False: "no_flags",
        }
    )
)
tables["review_counts"] = review_counts

# The February source contains country rows labelled NONE, which cannot
# be assigned to a country. Retain them in the audit and allow loading
# to continue; Stage 2 quarantines them before constructing the samples.
# Any other invalid geography identifier still stops this stage.
flags = tables["invalid_geo_ids"]
accepted_geo = (
    flags["source_id"].eq("release_2026_03_24")
    & flags["date_start"].eq("2026-02-05")
    & flags["date_end"].eq("2026-02-12")
    & flags["geo_level"].eq("country")
    & flags["geo_id"].eq("NONE")
)
unresolved = review_counts.loc[
    review_counts["flagged_rows"].gt(0)
    & review_counts["check"].ne("invalid_geo_ids")
]
# Keep one extracted table. Coverage needed for profile construction travels
# with its native records; audit detail belongs in the log and manifest.
records = records.merge(
    coverage[
        geography_key + ["candidate_complete_partition", "distinct_modes"]
    ],
    on=geography_key,
    validate="many_to_one",
)
records.insert(0, "run_id", run_id)
logging.info("Native records: %d", len(records))
logging.info("Review checks:\n%s", review_counts.to_string(index=False))
for name, table in tables.items():
    if name in review_names and not table.empty:
        logging.info("%s:\n%s", name, table.to_string(index=False))
if not unresolved.empty or not accepted_geo.all():
    raise ValueError(f"{RESULTS_DIR}: unaccepted source audit flags")
manifest["source_fingerprints"] = inventory_rows
manifest["source_windows"] = source_contract.to_dict(orient="records")
manifest["review_checks"] = review_counts.to_dict(orient="records")
manifest["accepted_NONE_rows"] = int(accepted_geo.sum())
manifest["selected_records"] = len(records)
output_files = write_tables(
    {"native_collaboration": records}, OUTPUT_NATIVE.parent
)
finish_stage(manifest, output_files)
