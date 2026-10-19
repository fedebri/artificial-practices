"""Build the single curated profile table used by all later stages.

Read audited native records and the original fingerprinted ISO crosswalk.
Resolve country identifiers, retain incomplete publication as missing values,
and reshape each observed geography/window once. Retain partial profiles and log unavailable roster countries. Membership
requires the declared number of source windows; absent rows are never zeros.

The output is results/02_build_profiles/profiles.csv.
Each country/window has one row. Published percentages, conditional shares,
coverage, source lineage and sample-membership flags live in this same table.
GLOBAL rows retain the publisher's separate aggregate.
G20 selection is simply profiles.loc[profiles["in_g20_common_five"]].

Audit findings and sample counts go to logs/practices.log and logs/run.json.
Missing modes are never zeros. Five-mode normalization conditions on classified
mass; stable countries do not establish stable users or measurement regimes.
"""

import hashlib
import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd

from artifacts import begin_stage, finish_stage, write_tables

INPUT_NATIVE = Path("data/interim/reproduction/native_collaboration.csv")
INPUT_RUN_LOG = Path("logs/run.json")
INPUT_CROSSWALK = Path(
    "data/raw/release_2025_09_15/data/intermediate/iso_country_codes.csv"
)
INPUT_SOURCE_LOCK = Path("docs/reproduction_sources.json")
OUTPUT_PROFILES = Path("results/02_build_profiles/profiles.csv")
RESULTS_DIR = Path("results/02_build_profiles")

manifest = begin_stage(
    RESULTS_DIR,
    (INPUT_NATIVE, INPUT_RUN_LOG, INPUT_CROSSWALK, INPUT_SOURCE_LOCK),
    seed=None,
    upstream_stages=("01_load_audit",),
)
run_id = manifest["run_id"]
upstream_manifest = json.loads(INPUT_RUN_LOG.read_text())["stages"][
    "01_load_audit"
]
# Read the original crosswalk under the same source lock audited in Stage 1.
# This also rejects edits to both the crosswalk and lock between the stages.
with INPUT_SOURCE_LOCK.open("rb") as handle:
    source_lock_digest = hashlib.file_digest(handle, "sha256").hexdigest()
if source_lock_digest != upstream_manifest["source_lock_sha256"]:
    raise ValueError(f"{INPUT_SOURCE_LOCK}: differs from {INPUT_RUN_LOG}")
source_lock = json.loads(INPUT_SOURCE_LOCK.read_text())["sha256"]
with INPUT_CROSSWALK.open("rb") as handle:
    crosswalk_digest = hashlib.file_digest(handle, "sha256").hexdigest()
if crosswalk_digest != source_lock[str(INPUT_CROSSWALK)]:
    raise ValueError(
        f"{INPUT_CROSSWALK}: differs from the frozen source SHA-256"
    )
manifest["crosswalk_sha256"] = crosswalk_digest

native = pd.read_csv(
    INPUT_NATIVE,
    keep_default_na=False,
    na_values=["<NA>"],
    float_precision="round_trip",
    dtype={"published_value": "string", "source_hierarchy_level": "string"},
).rename(columns={"run_id": "source_run_id", "geo_id": "native_geo_id"})
windows = pd.DataFrame(upstream_manifest["source_windows"])
window_key = ["source_id", "date_start", "date_end"]
country_window_key = window_key + ["country_iso3"]
native_country_window_key = window_key + ["native_geo_id"]
# NA is Namibia's valid alpha-2 code, so disable default missing-value parsing.
reference = pd.read_csv(
    INPUT_CROSSWALK,
    dtype="string",
    keep_default_na=False,
    usecols=["iso_alpha_2", "iso_alpha_3", "country_name"],
)
valid_reference = reference["iso_alpha_2"].str.fullmatch(
    r"[A-Z]{2}"
) & reference["iso_alpha_3"].str.fullmatch(r"[A-Z]{3}")
if not valid_reference.all():
    logging.error(
        "Invalid ISO rows:\n%s",
        reference.loc[~valid_reference].to_string(index=False),
    )
    raise ValueError(f"{RESULTS_DIR}: unresolved country mapping flags")
mapping = pd.concat(
    [
        reference.rename(
            columns={
                "iso_alpha_2": "native_geo_id",
                "iso_alpha_3": "country_iso3",
            }
        )[["native_geo_id", "country_iso3", "country_name"]],
        pd.DataFrame(
            {
                "native_geo_id": reference["iso_alpha_3"],
                "country_iso3": reference["iso_alpha_3"],
                "country_name": reference["country_name"],
            }
        ),
    ],
    ignore_index=True,
)

country_rows = native.loc[native["geo_level"].eq("country")].copy()
# NONE has no established country interpretation. Its source records stay in
# Stage 1's native table; the log explains why it never becomes a country row.
quarantined = country_rows.loc[country_rows["native_geo_id"].eq("NONE")]
logging.info(
    "Quarantined NONE records: %d\n%s",
    len(quarantined),
    quarantined.to_string(index=False),
)
mapping_input = country_rows.loc[country_rows["native_geo_id"].ne("NONE")]
joined = mapping_input.merge(
    mapping,
    on="native_geo_id",
    how="left",
    validate="many_to_one",
    indicator=True,
)
unmatched = joined.loc[joined["_merge"].eq("left_only")]
if not unmatched.empty:
    logging.error(
        "Unmatched country IDs:\n%s",
        unmatched[native_country_window_key]
        .drop_duplicates()
        .to_string(index=False),
    )
    raise ValueError(f"{RESULTS_DIR}: unresolved country mapping flags")
mapped = joined.drop(columns="_merge")
country_window_inventory = mapped[
    native_country_window_key + ["country_iso3", "country_name"]
].drop_duplicates()
collision = country_window_inventory.duplicated(country_window_key, keep=False)
if collision.any():
    logging.error(
        "Country ID collisions:\n%s",
        country_window_inventory.loc[collision].to_string(index=False),
    )
    raise ValueError(f"{RESULTS_DIR}: unresolved country mapping flags")

# One strict reshape keeps partial modes missing and rejects duplicate cells.
mapped["profile_geo_id"] = mapped["country_iso3"]
global_rows = native.loc[native["geo_level"].eq("global")].copy()
global_rows["profile_geo_id"] = global_rows["native_geo_id"]
combined = pd.concat([mapped, global_rows], ignore_index=True)
profile_key = window_key + ["geo_level", "profile_geo_id"]
profiles = combined.pivot(
    index=profile_key, columns="measure", values="published_pct"
).reindex(
    columns=[
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
profiles.columns = [f"published_{name}_pct" for name in profiles.columns]
profiles = profiles.reset_index().merge(
    combined[
        profile_key
        + [
            "native_geo_id",
            "country_iso3",
            "country_name",
            "source_schema",
            "source_run_id",
            "candidate_complete_partition",
        ]
    ].drop_duplicates(),
    on=profile_key,
    validate="one_to_one",
)
roster = pd.DataFrame(
    [
        ("ARG", "Argentina"),
        ("AUS", "Australia"),
        ("BRA", "Brazil"),
        ("CAN", "Canada"),
        ("CHN", "China"),
        ("FRA", "France"),
        ("DEU", "Germany"),
        ("IND", "India"),
        ("IDN", "Indonesia"),
        ("ITA", "Italy"),
        ("JPN", "Japan"),
        ("MEX", "Mexico"),
        ("RUS", "Russia"),
        ("SAU", "Saudi Arabia"),
        ("ZAF", "South Africa"),
        ("KOR", "South Korea"),
        ("TUR", "Türkiye"),
        ("GBR", "United Kingdom"),
        ("USA", "United States"),
    ],
    columns=["country_iso3", "country_label"],
)
# Keep observed geography/windows only. The required window counts below
# detect incomplete histories without manufacturing absent-country rows.
profiles = profiles.merge(windows, on=window_key, validate="many_to_one")
profiles["source_run_id"] = upstream_manifest["run_id"]
profiles["partition_eligible"] = profiles["candidate_complete_partition"].eq(
    True
)
profiles = profiles.drop(columns="candidate_complete_partition")
mode_pct = profiles[
    [
        "published_directive_pct",
        "published_feedback_loop_pct",
        "published_learning_pct",
        "published_task_iteration_pct",
        "published_validation_pct",
    ]
]
profiles["classified_total_pct"] = mode_pct.sum(axis=1, min_count=5)
invalid_global = (
    profiles["geo_level"].eq("global") & ~profiles["partition_eligible"]
)
if invalid_global.any():
    raise ValueError(f"{RESULTS_DIR}: incomplete publisher-global profile")
# Closure makes five fractions sum to one while preserving their published ratios.
# It conditions away none/unclassified mass;
# Published totals and coverage remain columns of this same table.
for mode in (
    "directive",
    "feedback_loop",
    "learning",
    "task_iteration",
    "validation",
):
    profiles[f"conditional_{mode}_share"] = (
        profiles[f"published_{mode}_pct"] / profiles["classified_total_pct"]
    )
profiles["automation_published_pct"] = profiles[
    ["published_directive_pct", "published_feedback_loop_pct"]
].sum(axis=1, min_count=2)
profiles["automation_conditional_share"] = (
    profiles["automation_published_pct"] / profiles["classified_total_pct"]
)
profiles["augmentation_published_pct"] = profiles[
    [
        "published_learning_pct",
        "published_task_iteration_pct",
        "published_validation_pct",
    ]
].sum(axis=1, min_count=3)
profiles["augmentation_conditional_share"] = (
    profiles["augmentation_published_pct"] / profiles["classified_total_pct"]
)
# Missing none/unclassified rows remain missing. The observed support
# sum is partial, so its gap from 100 is not automatically an
# unclassified-share estimate.
profiles["none_is_published"] = profiles["published_none_pct"].notna()
profiles["not_classified_is_published"] = profiles[
    "published_not_classified_pct"
].notna()
# This sum is observed support only; buckets are a separate
# classification.
profiles["observed_pattern_total_pct"] = profiles[
    [
        "classified_total_pct",
        "published_none_pct",
        "published_not_classified_pct",
    ]
].sum(axis=1, min_count=1)
profiles["observed_pattern_gap_to_100_pp"] = (
    100 - profiles["observed_pattern_total_pct"]
)
profiles["published_bucket_total_pct"] = profiles[
    [
        "published_bucket_automation_pct",
        "published_bucket_augmentation_pct",
    ]
].sum(axis=1, min_count=2)
profiles["bucket_automation_minus_conditional_pp"] = (
    profiles["published_bucket_automation_pct"]
    - 100 * profiles["automation_conditional_share"]
)
profiles["bucket_automation_minus_published_pp"] = (
    profiles["published_bucket_automation_pct"]
    - profiles["automation_published_pct"]
)

# Sample definitions stay explicit. A flag selects rows; it never creates a
# separate G20 dataset or repeats profile construction.
is_country = profiles["geo_level"].eq("country")
is_legacy = profiles["measurement_era"].eq("legacy")
is_monthly = profiles["measurement_era"].eq("monthly")
legacy_windows = int(windows["measurement_era"].eq("legacy").sum())
monthly_windows = int(windows["measurement_era"].eq("monthly").sum())
legacy_hits = (
    (profiles["partition_eligible"] & is_legacy)
    .groupby(profiles["profile_geo_id"])
    .transform("sum")
)
monthly_hits = (
    (profiles["partition_eligible"] & is_monthly)
    .groupby(profiles["profile_geo_id"])
    .transform("sum")
)
profiles["in_legacy_stable"] = (
    is_country & is_legacy & legacy_hits.eq(legacy_windows)
)
profiles["in_monthly_stable"] = (
    is_country & is_monthly & monthly_hits.eq(monthly_windows)
)
profiles["in_common_five"] = is_country & (legacy_hits + monthly_hits).eq(
    len(windows)
)
profiles["in_full_published"] = is_country & profiles["partition_eligible"]
profiles["is_g20_country"] = is_country & profiles["country_iso3"].isin(
    roster["country_iso3"]
)
profiles["in_g20_common_five"] = (
    profiles["is_g20_country"] & profiles["in_common_five"]
)
profiles["country_label"] = (
    profiles["country_iso3"]
    .map(roster.set_index("country_iso3")["country_label"])
    .fillna(profiles["country_name"])
)
profiles.loc[~is_country, "country_label"] = "GLOBAL"
if not profiles["in_g20_common_five"].any():
    raise ValueError(f"{RESULTS_DIR}: empty stable G20 sample")
logging.info(
    "Observed country/windows: %d; eligible five-mode profiles: %d",
    int(is_country.sum()),
    int(profiles["in_full_published"].sum()),
)
missing_g20 = sorted(
    set(roster["country_iso3"]) - set(profiles.loc[is_country, "country_iso3"])
)
logging.info("G20 roster countries absent from all sources: %s", missing_g20)
manifest["unpublished_g20_countries"] = missing_g20
counts = profiles.groupby(window_key)[
    [
        "in_legacy_stable",
        "in_monthly_stable",
        "in_common_five",
        "in_full_published",
        "in_g20_common_five",
    ]
].sum()
logging.info("Included countries by window:\n%s", counts.to_string())
manifest["sample_counts"] = counts.reset_index().to_dict(orient="records")
manifest["quarantined_records"] = len(quarantined)
manifest["row_counts"] = {
    "country_windows": int(is_country.sum()),
    "eligible_country_windows": int(profiles["in_full_published"].sum()),
    "global_windows": int((~is_country).sum()),
}
profiles.insert(0, "run_id", run_id)
output_files = write_tables({"profiles": profiles}, RESULTS_DIR)
finish_stage(manifest, output_files)
