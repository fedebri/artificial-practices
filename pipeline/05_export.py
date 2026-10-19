"""Assemble one validated scientific consumer interface from saved results.

Read the single curated profile table and the distinct distance, sensitivity
and model results. Core/G20 selections, long mode views, reporting counts and
nearest-peer views are temporary pandas operations, not separately saved data.
Preserve scientific identities, units, missingness and interpretation qualifiers.

Validate the Arrow schema and unique consumer grain once. Write only
consumer_metrics.csv (plus typed Parquet at 100+ rows), consumer_schema.json and
consumer_metadata.json under results/05_export. Source fingerprints,
producer IDs and execution accounting remain in the interface and metadata.
There are no copied tables/core or tables/g20 folders or compatibility datasets.

The unified interface carries both core and G20 rows. Keeping the original core
field types inside this schema preserves that contract without another export.
"""

import json
import logging
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from artifacts import (
    begin_stage,
    finish_stage,
)


INPUT_TABLES = {
    "window_summary": Path("results/03_estimate/window_summary.csv"),
    "contrasts": Path("results/04_sensitivity/contrasts.csv"),
    "rank_persistence": Path("results/04_sensitivity/rank_persistence.csv"),
    "influence_contrasts": Path(
        "results/04_sensitivity/influence_contrasts.csv"
    ),
    "mode_dispersion": Path("results/03_estimate/mode_dispersion.csv"),
    "fit_summary": Path("results/model_diagnostic/fit_summary.csv"),
    "model_comparison": Path("results/model_diagnostic/model_comparison.csv"),
    "coefficients": Path("results/model_diagnostic/coefficients.csv"),
    "model_contrasts": Path("results/model_diagnostic/model_contrasts.csv"),
}
INPUT_MODE_WINDOWS = Path(
    "results/04_sensitivity/mode_sensitivity_windows.csv"
)
INPUT_MODE_CONTRASTS = Path(
    "results/04_sensitivity/mode_sensitivity_contrasts.csv"
)
INPUT_INFLUENCE_SUMMARY = Path(
    "results/04_sensitivity/country_influence_summary.csv"
)
INPUT_PROFILES = Path("results/02_build_profiles/profiles.csv")
INPUT_RUN_LOG = Path("logs/run.json")
INPUT_G20_TABLES = {
    "pairwise_distances": Path("results/03_estimate/pairwise_distances.csv"),
    "country_distances": Path("results/03_estimate/country_distances.csv"),
    "window_summary": Path("results/03_estimate/window_summary.csv"),
    "mode_dispersion": Path("results/03_estimate/mode_dispersion.csv"),
    "contrasts": Path("results/04_sensitivity/contrasts.csv"),
    "country_changes": Path("results/04_sensitivity/country_changes.csv"),
    "pair_changes": Path("results/04_sensitivity/pair_changes.csv"),
    "rank_persistence": Path("results/04_sensitivity/rank_persistence.csv"),
    "country_influence": Path(
        "results/04_sensitivity/influence_contrasts.csv"
    ),
    "mode_sensitivity_windows": Path(
        "results/04_sensitivity/mode_sensitivity_windows.csv"
    ),
    "mode_sensitivity_contrasts": Path(
        ("results/04_sensitivity/" "mode_sensitivity_contrasts.csv")
    ),
}
RESULTS_DIR = Path("results/05_export")
OUTPUT_CONSUMER = Path("results/05_export/consumer_metrics.csv")
OUTPUT_METADATA = Path("results/05_export/consumer_metadata.json")
OUTPUT_SCHEMA = Path("results/05_export/consumer_schema.json")

# Require completed producers before assembling the consumer interface.
manifest = begin_stage(
    RESULTS_DIR,
    (
        *INPUT_TABLES.values(),
        INPUT_MODE_WINDOWS,
        INPUT_MODE_CONTRASTS,
        INPUT_INFLUENCE_SUMMARY,
        INPUT_PROFILES,
        INPUT_RUN_LOG,
        *INPUT_G20_TABLES.values(),
    ),
    seed=None,  # Export has no random operations.
    upstream_stages=(
        "01_load_audit",
        "02_build_profiles",
        "03_estimate",
        "04_sensitivity",
        "model_diagnostic",
    ),
)
run_id = manifest["run_id"]
run_log = json.loads(INPUT_RUN_LOG.read_text())
producers = {
    name: run_log["stages"][name] for name in manifest["upstream_stages"]
}
lineage = {
    "01_load_audit": producers["01_load_audit"]["run_id"],
    "02_build_sample": producers["02_build_profiles"]["run_id"],
    "03_construct_explore": producers["02_build_profiles"]["run_id"],
    "04_estimate_convergence": producers["03_estimate"]["run_id"],
    "05_descriptive_model": producers["model_diagnostic"]["run_id"],
}
# Separate broader-country rows for the core contract; G20 is exported below.
saved = {
    name: pd.read_csv(
        path,
        keep_default_na=False,
        na_values=["<NA>"],
        float_precision="round_trip",
    )
    for name, path in INPUT_TABLES.items()
}
# Reporting summaries are temporary views of the one curated table.
profiles = pd.read_csv(
    INPUT_PROFILES,
    keep_default_na=False,
    na_values=["<NA>"],
    float_precision="round_trip",
)
window_key = ["source_id", "date_start", "date_end"]
core_profiles = pd.concat(
    [
        profiles.loc[profiles[f"in_{sample_id}"]].assign(sample_id=sample_id)
        for sample_id in (
            "legacy_stable",
            "monthly_stable",
            "common_five",
            "full_published",
        )
    ],
    ignore_index=True,
)
global_profiles = profiles.loc[profiles["geo_level"].eq("global")].assign(
    sample_id="published_global"
)
descriptive_profiles = pd.concat(
    [core_profiles, global_profiles], ignore_index=True
)
saved["denominator_summary"] = descriptive_profiles.groupby(
    ["sample_id"] + window_key + ["measurement_era"], as_index=False
).agg(
    min_classified_total_pct=("classified_total_pct", "min"),
    median_classified_total_pct=("classified_total_pct", "median"),
    max_classified_total_pct=("classified_total_pct", "max"),
    none_published_profiles=("none_is_published", "sum"),
    not_classified_published_profiles=("not_classified_is_published", "sum"),
)
saved["global_summary"] = global_profiles
sample_summaries = []
for sample_id, era in (
    ("legacy_stable", "legacy"),
    ("monthly_stable", "monthly"),
    ("common_five", None),
    ("full_published", None),
):
    selected = profiles.loc[profiles["geo_level"].eq("country")]
    if era is not None:
        selected = selected.loc[selected["measurement_era"].eq(era)]
    summary = (
        selected.groupby(window_key, as_index=False)
        .agg(
            published_partitions=("profile_geo_id", "size"),
            eligible_partitions=("partition_eligible", "sum"),
            included_countries=(f"in_{sample_id}", "sum"),
        )
        .assign(sample_id=sample_id)
    )
    sample_summaries.append(summary)
saved["sample_summary"] = pd.concat(sample_summaries, ignore_index=True)
for name in (
    "window_summary",
    "contrasts",
    "rank_persistence",
    "influence_contrasts",
    "mode_dispersion",
    "sample_summary",
):
    saved[name] = (
        saved[name].loc[saved[name]["sample_id"].ne("g20_common_five")].copy()
    )
mode_windows = pd.read_csv(
    INPUT_MODE_WINDOWS,
    keep_default_na=False,
    na_values=["<NA>"],
    float_precision="round_trip",
)
mode_windows = mode_windows.loc[
    mode_windows["sample_id"].ne("g20_common_five")
].copy()
mode_contrasts = pd.read_csv(
    INPUT_MODE_CONTRASTS,
    keep_default_na=False,
    na_values=["<NA>"],
    float_precision="round_trip",
)
mode_contrasts = (
    mode_contrasts.loc[mode_contrasts["sample_id"].ne("g20_common_five")]
    .drop(
        columns=[
            "analysis_role",
            "design_id",
            "measurement_era_before",
            "measurement_era_after",
            "estimand",
            "measurement_equivalence",
            "behavioral_change_identified",
        ]
    )
    .copy()
)

# Preserve the reviewed core execution accounting and consumer units.
country_influence = pd.read_csv(
    INPUT_INFLUENCE_SUMMARY,
    keep_default_na=False,
    na_values=["<NA>"],
    float_precision="round_trip",
)
country_influence = country_influence.loc[
    country_influence["sample_id"].ne("g20_common_five")
].copy()
# Record executed, unavailable and deliberately omitted specifications.
account_rows = []
for row in saved["contrasts"].itertuples(index=False):
    account_rows.append(
        {
            "analysis_id": f"five_modes_{row.sample_id}_{row.contrast_id}",
            "sample_id": row.sample_id,
            "contrast_id": row.contrast_id,
            "variant": "five_modes",
            "planned": True,
            "status": "run",
            "method": "base-2 JS distance; equal unordered pairs",
            "note": row.analysis_role,
            "source_stage": "04_estimate_convergence",
            "source_run_id": lineage["04_estimate_convergence"],
            "result_location": "contrasts.csv",
        }
    )
for row in mode_contrasts.itertuples(index=False):
    account_rows.append(
        {
            "analysis_id": f"{row.variant}_{row.sample_id}_{row.contrast_id}",
            "sample_id": row.sample_id,
            "contrast_id": row.contrast_id,
            "variant": row.variant,
            "planned": True,
            "status": "run" if row.status == "computed" else "not run",
            "method": "four-mode conditional JS; fixed membership",
            "note": row.endpoint_statuses,
            "source_stage": "06_evaluate_export",
            "source_run_id": run_id,
            "result_location": "mode_sensitivity_contrasts.csv",
        }
    )
for row in country_influence.itertuples(index=False):
    account_rows.append(
        {
            "analysis_id": (
                f"country_influence_{row.sample_id}_" f"{row.contrast_id}"
            ),
            "sample_id": row.sample_id,
            "contrast_id": row.contrast_id,
            "variant": "leave_one_country",
            "planned": True,
            "status": "run" if row.available_checks else "not run",
            "method": "remove same shared country at both endpoints",
            "note": (
                f"{row.available_checks}/{row.checks} removals available; "
                "no interval"
            ),
            "source_stage": "04_estimate_convergence",
            "source_run_id": lineage["04_estimate_convergence"],
            "result_location": "influence_contrasts.csv",
        }
    )
for row in saved["fit_summary"].itertuples(index=False):
    account_rows.append(
        {
            "analysis_id": f"model_{row.sample_id}_{row.model_id}",
            "sample_id": row.sample_id,
            "variant": row.model_id,
            "planned": True,
            "status": "run",
            "method": row.specification,
            "note": (
                (
                    "descriptive projection; window effects duplicate "
                    "direct changes"
                )
            ),
            "source_stage": "05_descriptive_model",
            "source_run_id": lineage["05_descriptive_model"],
            "result_location": "fit_summary.csv",
        }
    )
for analysis, stage, location, method in (
    (
        "sample_alternatives",
        "02_build_sample",
        "sample_summary.csv",
        "era-stable, common-five, full per-window targets",
    ),
    (
        "denominators_global",
        "03_construct_explore",
        "denominator_summary.csv",
        "retain original scales, auxiliary labels, and global context",
    ),
    (
        "automation_denominators",
        "04_estimate_convergence",
        "window_summary.csv",
        "conditional versus original published automation; ddof=0",
    ),
    (
        "automation_rank_persistence",
        "04_estimate_convergence",
        "rank_persistence.csv",
        "Spearman on shared countries; undefined constants retained",
    ),
    (
        "mode_dispersion",
        "04_estimate_convergence",
        "mode_dispersion.csv",
        "conditional SD by mode; no additive distance interpretation",
    ),
):
    account_rows.append(
        {
            "analysis_id": analysis,
            "planned": True,
            "status": "run",
            "method": method,
            "note": "see saved statuses and target populations",
            "source_stage": stage,
            "source_run_id": lineage[stage],
            "result_location": location,
        }
    )
for analysis, reason in (
    (
        "conversation_sampling_uncertainty",
        "no justified sampling/inferential design",
    ),
    ("cross_break_trend", "measurement sequences are compared separately"),
):
    account_rows.append(
        {
            "analysis_id": analysis,
            "planned": False,
            "status": "not run",
            "method": "omitted by design",
            "note": reason,
            "source_stage": "06_evaluate_export",
            "source_run_id": run_id,
            "result_location": "analysis_accounting.csv",
        }
    )
accounting = pd.DataFrame(account_rows)
# Reshape named metrics into long rows with explicit units and provenance.
consumer_frames = []
for table_name, frame, units, source_stage in (
    (
        "window_summary",
        saved["window_summary"],
        {
            "mean_js_distance": "JS distance (base 2)",
            "automation_mean_share": "fraction",
            "automation_sd_share": "fraction",
            "automation_published_mean_share": (
                "fraction of published " "denominator"
            ),
            "automation_published_sd_share": (
                "fraction of published " "denominator"
            ),
        },
        "04_estimate_convergence",
    ),
    (
        "contrasts",
        saved["contrasts"],
        {
            "mean_js_distance_before": "JS distance (base 2)",
            "mean_js_distance_after": "JS distance (base 2)",
            "mean_js_distance_change": (
                "JS distance change " "(after minus before)"
            ),
            "automation_mean_share_change": "fraction change",
            "automation_sd_share_change": "fraction change",
        },
        "04_estimate_convergence",
    ),
    (
        "rank_persistence",
        saved["rank_persistence"].rename(columns={"status": "note"}),
        {
            "spearman_automation": "Spearman correlation",
        },
        "04_estimate_convergence",
    ),
    (
        "mode_dispersion",
        saved["mode_dispersion"].rename(columns={"mode": "variant"}),
        {
            "sd_conditional_share": "fraction",
            "mean_conditional_share": "fraction",
        },
        "04_estimate_convergence",
    ),
    (
        "denominator_summary",
        saved["denominator_summary"],
        {
            "min_classified_total_pct": "percentage points",
            "median_classified_total_pct": "percentage points",
            "max_classified_total_pct": "percentage points",
            "none_published_profiles": "count",
            "not_classified_published_profiles": "count",
        },
        "03_construct_explore",
    ),
    (
        "global_summary",
        saved["global_summary"],
        {
            "published_directive_pct": "percentage points",
            "published_feedback_loop_pct": "percentage points",
            "published_learning_pct": "percentage points",
            "published_task_iteration_pct": "percentage points",
            "published_validation_pct": "percentage points",
            "published_none_pct": "percentage points",
            "published_not_classified_pct": "percentage points",
            "classified_total_pct": "percentage points",
            "automation_published_pct": "percentage points",
            "automation_conditional_share": "fraction",
        },
        "03_construct_explore",
    ),
    (
        "sample_summary",
        saved["sample_summary"],
        {
            "published_partitions": "count",
            "eligible_partitions": "count",
            "included_countries": "count",
        },
        "02_build_sample",
    ),
    (
        "fit_summary",
        saved["fit_summary"].rename(columns={"model_id": "variant"}),
        {
            "observations": "count",
            "countries": "count",
            "windows": "count",
            "parameters": "count",
            "rank": "count",
            "residual_df": "count",
            "condition_number": "condition number",
            "rmse": "JS distance (base 2)",
            "sse": "squared JS distance",
            "r_squared": "R-squared",
        },
        "05_descriptive_model",
    ),
    (
        "model_comparison",
        saved["model_comparison"].rename(
            columns={"within_country_sse_status": "note"}
        ),
        {
            "baseline_sse": "squared JS distance",
            "country_window_sse": "squared JS distance",
            "within_country_sse_explained": (
                "fraction of baseline " "residual SSE"
            ),
        },
        "05_descriptive_model",
    ),
    (
        "coefficients",
        saved["coefficients"].rename(columns={"model_id": "variant"}),
        {
            "estimate": "JS distance (base 2)",
        },
        "05_descriptive_model",
    ),
    (
        "model_contrasts",
        saved["model_contrasts"],
        {
            "model_window_contrast": (
                "JS distance change " "(after minus before)"
            ),
            "absolute_error": "JS distance (base 2)",
        },
        "05_descriptive_model",
    ),
    (
        "mode_sensitivity_windows",
        mode_windows.rename(columns={"status": "note"}),
        {
            "mean_js_distance": "four-mode JS distance (base 2)",
            "invalid_remaining_mass_profiles": "count",
        },
        "06_evaluate_export",
    ),
    (
        "mode_sensitivity_contrasts",
        mode_contrasts.rename(columns={"endpoint_statuses": "note"}),
        {
            "mean_js_distance_change": "four-mode JS distance change",
        },
        "06_evaluate_export",
    ),
    (
        "country_influence_summary",
        country_influence,
        {
            "minimum_leaveout_change": "JS distance change; not an interval",
            "maximum_leaveout_change": "JS distance change; not an interval",
            "available_checks": "count",
            "checks": "count",
        },
        "06_evaluate_export",
    ),
):
    id_columns = [
        name
        for name in (
            "sample_id",
            "source_id",
            "date_start",
            "date_end",
            "date_before",
            "date_after",
            "contrast_id",
            "measurement_era",
            "countries",
            "countries_before",
            "countries_after",
            "variant",
            "term",
            "note",
            "countries_shared",
            "sample_target",
            "analysis_role",
            "reference_window",
            "specification",
            "r_squared_definition",
        )
        if name in frame.columns and name not in units
    ]
    long = frame.melt(
        id_vars=id_columns,
        value_vars=list(units),
        var_name="metric",
        value_name="value",
    ).rename(columns={"value": "estimate"})
    if "countries" in long:
        long["countries_before"] = long["countries"]
        long["countries_after"] = long["countries"]
    long["table"] = table_name
    long["unit"] = long["metric"].map(units)
    long["status"] = np.where(
        long["estimate"].notna(), "computed", "unavailable"
    )
    long["source_stage"] = source_stage
    long["source_run_id"] = (
        run_id
        if source_stage == "06_evaluate_export"
        else lineage[source_stage]
    )
    consumer_frames.append(long)
account_consumer = accounting.copy()
account_consumer["table"] = "analysis_accounting"
account_consumer["metric"] = "execution"
account_consumer["estimate"] = np.nan
account_consumer["unit"] = "status"
account_consumer["note"] = accounting["method"] + "; " + accounting["note"]
consumer_frames.append(account_consumer)
consumer = pd.concat(consumer_frames, ignore_index=True)
consumer["run_id"] = run_id
consumer["design_id"] = "convergence_v1"
consumer["uncertainty"] = "not_estimated"


# Derive provenance from actual input artifact paths. A former stage may
# now span several responsibilities; its old label cannot identify the
# new producer of a temporal contrast or sensitivity result.
table_paths = {
    **INPUT_TABLES,
    "sample_summary": OUTPUT_CONSUMER,
    "denominator_summary": OUTPUT_CONSUMER,
    "global_summary": INPUT_PROFILES,
    "mode_sensitivity_windows": INPUT_MODE_WINDOWS,
    "mode_sensitivity_contrasts": INPUT_MODE_CONTRASTS,
    "country_influence_summary": INPUT_INFLUENCE_SUMMARY,
    "analysis_accounting": OUTPUT_CONSUMER,
}
for table_name, path in table_paths.items():
    producer_stage = path.relative_to("results").parts[0]
    producer_run = (
        run_id
        if producer_stage == "05_export"
        else producers[producer_stage]["run_id"]
    )
    rows = consumer["table"].eq(table_name)
    consumer.loc[rows, "source_stage"] = producer_stage
    consumer.loc[rows, "source_run_id"] = producer_run
for index, row in accounting.iterrows():
    table_name = Path(row["result_location"]).stem
    producer_stage = table_paths[table_name].relative_to("results").parts[0]
    accounting.loc[index, "source_stage"] = producer_stage
    accounting.loc[index, "source_run_id"] = (
        run_id
        if producer_stage == "05_export"
        else producers[producer_stage]["run_id"]
    )
account_origins = accounting.set_index("analysis_id")
account_rows = consumer["table"].eq("analysis_accounting")
for column in ("source_stage", "source_run_id"):
    consumer.loc[account_rows, column] = consumer.loc[
        account_rows, "analysis_id"
    ].map(account_origins[column])
locations = {
    name: str(Path("..") / path.relative_to("results"))
    for name, path in table_paths.items()
}
consumer["result_location"] = consumer["table"].map(locations)
accounting["result_location"] = accounting["result_location"].map(
    lambda name: locations[Path(name).stem]
)
core_consumer = consumer.copy()
g20_tables = {
    name: pd.read_csv(
        path,
        keep_default_na=False,
        na_values=["<NA>"],
        float_precision="round_trip",
    )
    for name, path in INPUT_G20_TABLES.items()
}
for name, frame in g20_tables.items():
    if "sample_id" in frame:
        g20_tables[name] = frame.loc[
            frame["sample_id"].eq("g20_common_five")
        ].copy()
# G20 is a row selection, followed by presentation reshaping in memory.
g20 = profiles.loc[profiles["in_g20_common_five"]]
id_columns = window_key + ["country_iso3", "country_label"]
published = g20.melt(
    id_vars=id_columns,
    value_vars=[
        "published_directive_pct",
        "published_feedback_loop_pct",
        "published_learning_pct",
        "published_task_iteration_pct",
        "published_validation_pct",
    ],
    var_name="mode",
    value_name="published_pct",
)
published["mode"] = (
    published["mode"].str.removeprefix("published_").str.removesuffix("_pct")
)
conditional = g20.melt(
    id_vars=id_columns,
    value_vars=[
        "conditional_directive_share",
        "conditional_feedback_loop_share",
        "conditional_learning_share",
        "conditional_task_iteration_share",
        "conditional_validation_share",
    ],
    var_name="mode",
    value_name="conditional_share",
)
conditional["mode"] = (
    conditional["mode"]
    .str.removeprefix("conditional_")
    .str.removesuffix("_share")
)
g20_tables["mode_shares"] = published.merge(
    conditional, on=id_columns + ["mode"], validate="one_to_one"
)
g20_tables["mode_shares"]["conditional_pct"] = (
    100 * g20_tables["mode_shares"]["conditional_share"]
)
g20_tables["mode_shares"]["sample_id"] = "g20_common_five"
# Nearest-peer flags were calculated with the distances. These are filtered
# views of those same pairs, retaining both orientations and all exact ties.
pairs = g20_tables["pairwise_distances"]
peer_keys = ["sample_id"] + window_key + ["measurement_era", "countries"]
peer_frames = []
for flag, country, peer, label, peer_label in (
    ("nearest_for_i", "country_i", "country_j", "label_i", "label_j"),
    ("nearest_for_j", "country_j", "country_i", "label_j", "label_i"),
):
    peer_frames.append(
        pairs.loc[
            pairs[flag],
            peer_keys + [country, peer, label, peer_label, "js_distance"],
        ].rename(
            columns={
                country: "country_iso3",
                peer: "peer_iso3",
                label: "country_label",
                peer_label: "peer_label",
            }
        )
    )
g20_tables["nearest_peers"] = pd.concat(peer_frames, ignore_index=True)
g20_sources = {
    **INPUT_G20_TABLES,
    "mode_shares": INPUT_PROFILES,
    "nearest_peers": INPUT_G20_TABLES["pairwise_distances"],
}

# G20 rows extend the same interface with country/pair identities. Units
# distinguish conditional fractions, percentage points and distance
# levels.
g20_frames = []
for name, units in (
    (
        "window_summary",
        {
            "mean_js_distance": "JS distance (base 2)",
            "automation_mean_share": "fraction",
            "automation_sd_share": "fraction",
            "automation_published_mean_share": (
                "fraction of published " "denominator"
            ),
            "automation_published_sd_share": (
                "fraction of published " "denominator"
            ),
        },
    ),
    (
        "contrasts",
        {
            "mean_js_distance_before": "JS distance (base 2)",
            "mean_js_distance_after": "JS distance (base 2)",
            "mean_js_distance_change": (
                "JS distance change " "(after minus before)"
            ),
            "relative_distance_change_pct": "percent change",
            "automation_mean_share_change": "fraction change",
            "automation_sd_share_change": "fraction change",
        },
    ),
    (
        "country_changes",
        {
            "mean_js_distance_before": "JS distance (base 2)",
            "mean_js_distance_after": "JS distance (base 2)",
            "mean_js_distance_change": (
                "JS distance change " "(after minus before)"
            ),
            "own_profile_js_distance": "own-profile JS distance (base 2)",
            "automation_change_pp": "percentage points",
            "coverage_change_pp": "percentage points",
            "directive_change_pp": "percentage points",
            "feedback_loop_change_pp": "percentage points",
            "learning_change_pp": "percentage points",
            "task_iteration_change_pp": "percentage points",
            "validation_change_pp": "percentage points",
        },
    ),
    (
        "pair_changes",
        {
            "js_distance_before": "JS distance (base 2)",
            "js_distance_after": "JS distance (base 2)",
            "js_distance_change": (
                "JS distance change " "(after minus before)"
            ),
        },
    ),
    (
        "pairwise_distances",
        {
            "js_distance": "JS distance (base 2)",
            "automation_gap_pp": "percentage points",
        },
    ),
    (
        "country_distances",
        {
            "mean_js_distance": "JS distance (base 2)",
            "nearest_js_distance": "JS distance (base 2)",
            "farthest_js_distance": "JS distance (base 2)",
        },
    ),
    ("nearest_peers", {"js_distance": "JS distance (base 2)"}),
    (
        "mode_shares",
        {
            "conditional_pct": "percent among five modes",
            "published_pct": "published percentage points",
        },
    ),
    (
        "mode_dispersion",
        {
            "mean_conditional_share": "fraction",
            "sd_conditional_share": "fraction",
        },
    ),
    ("rank_persistence", {"spearman_rho": "Spearman correlation"}),
    (
        "country_influence",
        {
            "excluded_distance_change": "JS distance change; not an interval",
            "excluded_minus_full": "JS distance change; not an interval",
        },
    ),
    (
        "mode_sensitivity_windows",
        {
            "mean_js_distance": "four-mode JS distance (base 2)",
            "zero_remaining_mass_countries": "count",
        },
    ),
    (
        "mode_sensitivity_contrasts",
        {"mean_js_distance_change": "four-mode JS distance change"},
    ),
):
    frame = g20_tables[name].copy()
    if "status" in frame:
        frame["note"] = frame["status"]
    id_columns = [
        column
        for column in (
            "sample_id",
            "source_id",
            "date_start",
            "date_end",
            "date_before",
            "date_after",
            "contrast_id",
            "measurement_era",
            "measurement_era_before",
            "measurement_era_after",
            "countries",
            "countries_before",
            "countries_after",
            "countries_shared",
            "variant",
            "country_iso3",
            "country_label",
            "country_i",
            "country_j",
            "label_i",
            "label_j",
            "peer_iso3",
            "peer_label",
            "rank_type",
            "omitted_mode",
            "mode",
            "removed_country_iso3",
            "removed_country_label",
            "analysis_role",
            "design_id",
            "estimand",
            "measurement_equivalence",
            "behavioral_change_identified",
            "note",
        )
        if column in frame and column not in units
    ]
    long = frame.melt(
        id_vars=id_columns,
        value_vars=list(units),
        var_name="metric",
        value_name="estimate",
    )
    if name == "country_changes":
        long = long.loc[
            long["metric"].ne("own_profile_js_distance")
            | long["contrast_id"].eq("august_may_cross_regime")
        ].copy()
    long["table"] = f"g20_{name}"
    long["unit"] = long["metric"].map(units)
    long["status"] = np.where(
        long["estimate"].notna(), "computed", "unavailable"
    )
    if "design_id" not in long:
        long["design_id"] = "g20_profiles_v1"
    if "countries" in long:
        long["countries_before"] = long["countries"]
        long["countries_after"] = long["countries"]
    producer_stage = g20_sources[name].relative_to("results").parts[0]
    long["source_stage"] = producer_stage
    long["source_run_id"] = producers[producer_stage]["run_id"]
    long["run_id"] = run_id
    long["uncertainty"] = "not_estimated"
    g20_frames.append(long)
consumer = pd.concat([core_consumer, *g20_frames], ignore_index=True)

# Validate the entire interface once. Reports consume the saved
# artifact; they neither repeat validation nor import analytical code.
core_schema = pa.schema(
    [
        pa.field("run_id", pa.string(), nullable=False),
        pa.field("design_id", pa.string(), nullable=False),
        pa.field("table", pa.string(), nullable=False),
        pa.field("sample_id", pa.string()),
        pa.field("source_id", pa.string()),
        pa.field("measurement_era", pa.string()),
        pa.field("sample_target", pa.string()),
        pa.field("analysis_role", pa.string()),
        pa.field("date_start", pa.string()),
        pa.field("date_end", pa.string()),
        pa.field("date_before", pa.string()),
        pa.field("date_after", pa.string()),
        pa.field("contrast_id", pa.string()),
        pa.field("variant", pa.string()),
        pa.field("term", pa.string()),
        pa.field("analysis_id", pa.string()),
        pa.field("reference_window", pa.string()),
        pa.field("specification", pa.string()),
        pa.field("r_squared_definition", pa.string()),
        pa.field("planned", pa.bool_()),
        pa.field("metric", pa.string(), nullable=False),
        pa.field("estimate", pa.float64()),
        pa.field("unit", pa.string(), nullable=False),
        pa.field("countries_before", pa.int64()),
        pa.field("countries_after", pa.int64()),
        pa.field("countries_shared", pa.int64()),
        pa.field("status", pa.string(), nullable=False),
        pa.field("note", pa.string()),
        pa.field("result_location", pa.string()),
        pa.field("source_stage", pa.string(), nullable=False),
        pa.field("source_run_id", pa.string(), nullable=False),
        pa.field("uncertainty", pa.string(), nullable=False),
    ],
    metadata={b"schema_version": b"convergence_consumer_v1"},
)
schema = pa.schema(
    [
        *core_schema,
        pa.field("country_iso3", pa.string()),
        pa.field("country_label", pa.string()),
        pa.field("country_i", pa.string()),
        pa.field("country_j", pa.string()),
        pa.field("label_i", pa.string()),
        pa.field("label_j", pa.string()),
        pa.field("peer_iso3", pa.string()),
        pa.field("peer_label", pa.string()),
        pa.field("rank_type", pa.string()),
        pa.field("omitted_mode", pa.string()),
        pa.field("mode", pa.string()),
        pa.field("removed_country_iso3", pa.string()),
        pa.field("removed_country_label", pa.string()),
        pa.field("measurement_era_before", pa.string()),
        pa.field("measurement_era_after", pa.string()),
        pa.field("estimand", pa.string()),
        pa.field("measurement_equivalence", pa.string()),
        pa.field("behavioral_change_identified", pa.bool_()),
    ],
    metadata={b"schema_version": b"artificial_practices_consumer_v2"},
)
consumer = consumer.reindex(columns=schema.names)
grain = [
    "table",
    "sample_id",
    "source_id",
    "date_start",
    "date_end",
    "date_before",
    "date_after",
    "contrast_id",
    "variant",
    "term",
    "analysis_id",
    "metric",
    "country_iso3",
    "country_i",
    "country_j",
    "peer_iso3",
    "rank_type",
    "omitted_mode",
    "mode",
    "removed_country_iso3",
]
if consumer.duplicated(grain).any():
    raise ValueError("Duplicate consumer keys; inspect the export mappings")
arrow_table = pa.Table.from_pandas(
    consumer, schema=schema, preserve_index=False, safe=True
)
arrow_table.validate(full=True)
# The validated consumer is the sole exported data interface. Small tables
# remain CSV-only; the Parquet copy retains the validated Arrow field types.
arrow_table.to_pandas().to_csv(OUTPUT_CONSUMER, index=False, na_rep="<NA>")
output_files = [OUTPUT_CONSUMER]
if len(arrow_table) >= 100:
    pq.write_table(arrow_table, OUTPUT_CONSUMER.with_suffix(".parquet"))
    output_files.append(OUTPUT_CONSUMER.with_suffix(".parquet"))
# Write field definitions and source/producer lineage beside the data.
OUTPUT_SCHEMA.write_text(
    json.dumps(
        {
            "schema_version": "artificial_practices_consumer_v2",
            "grain": grain,
            "fields": [
                {
                    "name": field.name,
                    "type": str(field.type),
                    "nullable": field.nullable,
                }
                for field in schema
            ],
        },
        indent=2,
    )
    + "\n"
)
OUTPUT_METADATA.write_text(
    json.dumps(
        {
            "schema_version": "artificial_practices_consumer_v2",
            "run_id": run_id,
            "release_status": "working_reproduction",
            "producer_runs": {
                name: producer["run_id"]
                for name, producer in producers.items()
            },
            "source_fingerprints": producers["01_load_audit"][
                "source_fingerprints"
            ],
            "weights": (
                "equal countries and distinct unordered pairs "
                "within each named sample"
            ),
            "uncertainty": "not estimated; no confidence level or p-values",
            "historical_cross_regime_status": (
                "one reviewed execution; no separate historical "
                "clean replay"
            ),
            "reference_comparison": (
                "see logs/verification.json after make verify-practices"
            ),
            "consumer_rows": len(consumer),
            "core_consumer_rows": len(core_consumer),
        },
        indent=2,
    )
    + "\n"
)
logging.info(
    "Exported %d consumer rows (%d core)", len(consumer), len(core_consumer)
)
finish_stage(manifest, [*output_files, OUTPUT_METADATA, OUTPUT_SCHEMA])
