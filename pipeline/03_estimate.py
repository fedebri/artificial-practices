"""Estimate distances from row selections of the one curated profile table.

Read results/02_build_profiles/profiles.csv after Stage 2 completes.
Each sample is selected by its in_<sample> column. G20 uses the same profiles
with its own peer population; filtering a wider-population distance would change
that estimand. No separate sample datasets or preparation runs are needed.

Use SciPy's base-2 Jensen-Shannon distance, equally weighted unordered pairs
and finite-country automation dispersion. Save four distinct result tables:
pairwise_distances, country_distances (including leave-one-out quantities),
window_summary and mode_dispersion. Nearest-peer ties are flags on the pairs.
All four tables use CSV; only pairwise_distances also gets Parquet at 100+ rows.
Numerical checks are recorded in logs/practices.log and logs/run.json.

These are descriptive distances between published aggregate compositions.
Pair dependence and changing measurement prevent causal or sampling inference.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial.distance import jensenshannon

from artifacts import (
    begin_stage,
    finish_stage,
    write_tables,
)


INPUT_PROFILES = Path("results/02_build_profiles/profiles.csv")
RESULTS_DIR = Path("results/03_estimate")
OUTPUT_PAIRS_PARQUET = Path("results/03_estimate/pairwise_distances.parquet")
manifest = begin_stage(
    RESULTS_DIR,
    (INPUT_PROFILES,),
    seed=None,
    upstream_stages=("02_build_profiles",),
)
run_id = manifest["run_id"]
profiles = pd.read_csv(
    INPUT_PROFILES,
    keep_default_na=False,
    na_values=["<NA>"],
    float_precision="round_trip",
)
window_key = ["source_id", "date_start", "date_end"]
pair_frames = []
country_rows = []
summary_rows = []
influence_rows = []
mode_rows = []
diagnostic_rows = []
# Each population is a row selection from the same curated table. G20 does
# not repeat curation; its distances are computed against its own peers.
for sample_id in (
    "legacy_stable",
    "monthly_stable",
    "common_five",
    "full_published",
    "g20_common_five",
):
    selected = profiles.loc[profiles[f"in_{sample_id}"]]
    for (source_id, date_start, date_end), group in selected.groupby(
        window_key
    ):
        group = group.sort_values("country_iso3").copy()
        if sample_id != "g20_common_five":
            group["country_label"] = group["country_name"]
        measurement_era = group["measurement_era"].iloc[0]
        n = len(group)
        meta = {
            "sample_id": sample_id,
            "source_id": source_id,
            "date_start": date_start,
            "date_end": date_end,
            "measurement_era": measurement_era,
            "sample_target": (
                "changing published population"
                if sample_id == "full_published"
                else "fixed country population"
            ),
            "countries": n,
            "pairs": n * (n - 1) // 2,
        }
        logging.info(
            "%s %s: %d countries; %d distinct pairs",
            sample_id,
            date_start,
            n,
            meta["pairs"],
        )
        matrix = group[
            [
                "conditional_directive_share",
                "conditional_feedback_loop_share",
                "conditional_learning_share",
                "conditional_task_iteration_share",
                "conditional_validation_share",
            ]
        ].to_numpy(dtype=float)
        # The upper triangle gives n(n-1)/2 unordered pairs, excluding self
        # pairs. Every country appears n-1 times and therefore receives
        # equal representation.
        left, right = np.triu_indices(n, k=1)
        if len(left):
            # SciPy returns sqrt(JS divergence): d(p,q) = sqrt((KL(p||m) +
            # KL(q||m))/2), with m = (p+q)/2. Base 2 bounds distance by 1
            # and supports explicit zeros without pseudocounts. The ordered
            # mode columns must agree for both countries.
            distances = jensenshannon(
                matrix[left], matrix[right], base=2, axis=1
            )
            mean_distance = float(np.mean(distances))
        else:
            distances = np.array([], dtype=float)
            mean_distance = np.nan
        codes = group["country_iso3"].to_numpy()
        pairs = pd.DataFrame(
            {
                "country_i": codes[left],
                "country_j": codes[right],
                "js_distance": distances,
            }
        ).assign(**meta)
        # Retain the dimensions behind the scalar distance for peer
        # inspection.
        labels = group["country_label"].to_numpy()
        automation_pct = 100 * group["automation_conditional_share"].to_numpy()
        classified = group["classified_total_pct"].to_numpy()
        pairs["label_i"] = labels[left]
        pairs["label_j"] = labels[right]
        pairs["automation_i_pct"] = automation_pct[left]
        pairs["automation_j_pct"] = automation_pct[right]
        pairs["automation_gap_pp"] = 100 * np.abs(
            group["automation_conditional_share"].to_numpy()[left]
            - group["automation_conditional_share"].to_numpy()[right]
        )
        pairs["classified_total_i_pct"] = classified[left]
        pairs["classified_total_j_pct"] = classified[right]
        for column, mode in enumerate(
            (
                "directive",
                "feedback_loop",
                "learning",
                "task_iteration",
                "validation",
            )
        ):
            pairs[f"{mode}_i_pct"] = 100 * matrix[left, column]
            pairs[f"{mode}_j_pct"] = 100 * matrix[right, column]
        pairs["nearest_for_i"] = False
        pairs["nearest_for_j"] = False
        pair_frames.append(pairs)

        country_means = []
        for index, country in enumerate(group.itertuples(index=False)):
            # Mean distance to peers differs from distance to a pooled
            # composition and from this country's change relative to its own
            # previous profile.
            own_distances = distances[(left == index) | (right == index)]
            country_mean = (
                float(np.mean(own_distances)) if len(own_distances) else np.nan
            )
            # Retain all exact nearest-peer ties as flags on the original pairs.
            if len(own_distances):
                pairs.loc[left == index, "nearest_for_i"] = (
                    distances[left == index] == own_distances.min()
                )
                pairs.loc[right == index, "nearest_for_j"] = (
                    distances[right == index] == own_distances.min()
                )
            country_means.append(country_mean)
            country_rows.append(
                {
                    **meta,
                    "country_iso3": country.country_iso3,
                    "country_name": country.country_name,
                    "country_label": country.country_label,
                    "classified_total_pct": country.classified_total_pct,
                    "nearest_js_distance": (
                        float(own_distances.min())
                        if len(own_distances)
                        else np.nan
                    ),
                    "farthest_js_distance": (
                        float(own_distances.max())
                        if len(own_distances)
                        else np.nan
                    ),
                    "mean_js_distance": country_mean,
                    "peer_countries": n - 1,
                    "automation_conditional_share": (
                        country.automation_conditional_share
                    ),
                }
            )
            # Removing a country deletes every pair touching it. This
            # measures deterministic influence, not a jackknife standard
            # error or interval.
            remaining = distances[(left != index) & (right != index)]
            loo_mean = float(np.mean(remaining)) if len(remaining) else np.nan
            influence_rows.append(
                {
                    **meta,
                    "country_iso3": country.country_iso3,
                    "country_name": country.country_name,
                    "mean_js_distance": mean_distance,
                    "country_mean_js_distance": country_mean,
                    "remaining_countries": n - 1,
                    "leave_one_out_mean_js_distance": loo_mean,
                    "leave_one_out_minus_full": loo_mean - mean_distance,
                    "status": (
                        "computed" if n >= 3 else "unavailable_fewer_than_two"
                    ),
                }
            )

        # A common automation level shift need not imply convergence. Report
        # mean and dispersion separately, plus the published-denominator
        # alternative on exactly the same countries. ddof=0 describes this
        # finite country set.
        automation = group["automation_conditional_share"].to_numpy(
            dtype=float
        )
        published_automation = (
            group["automation_published_pct"].to_numpy(dtype=float) / 100
        )
        summary_rows.append(
            {
                **meta,
                "mean_js_distance": mean_distance,
                "distance_status": (
                    "computed" if n >= 2 else "unavailable_fewer_than_two"
                ),
                "automation_mean_share": (
                    float(np.mean(automation)) if n else np.nan
                ),
                "automation_sd_share": (
                    float(np.std(automation, ddof=0)) if n else np.nan
                ),
                "automation_published_mean_share": (
                    float(np.mean(published_automation)) if n else np.nan
                ),
                "automation_published_sd_share": (
                    float(np.std(published_automation, ddof=0))
                    if n
                    else np.nan
                ),
            }
        )
        for column, mode in enumerate(
            (
                "directive",
                "feedback_loop",
                "learning",
                "task_iteration",
                "validation",
            )
        ):
            mode_rows.append(
                {
                    **meta,
                    "mode": mode,
                    "mean_conditional_share": (
                        float(np.mean(matrix[:, column])) if n else np.nan
                    ),
                    "sd_conditional_share": (
                        float(np.std(matrix[:, column], ddof=0))
                        if n
                        else np.nan
                    ),
                }
            )
        # Each pair contributes to two country averages, so their mean must
        # equal the pairwise mean. This tests bookkeeping rather than
        # substantive validity.
        identity_error = (
            abs(float(np.mean(country_means)) - mean_distance)
            if n >= 2
            else np.nan
        )
        distance_values_valid = bool(
            np.isfinite(distances).all()
            and (distances >= 0).all()
            and (distances <= 1 + 1e-12).all()
        )
        diagnostic_rows.append(
            {
                **meta,
                "distance_values_valid": distance_values_valid,
                "country_pair_mean_identity_abs_error": identity_error,
                "flagged": n >= 2
                and (
                    not distance_values_valid
                    or not np.isclose(identity_error, 0, atol=1e-12, rtol=0)
                ),
                "status": (
                    "checked" if n >= 2 else "unavailable_fewer_than_two"
                ),
            }
        )

    # Combine results as labelled sample branches; each keeps its own peer frame.
pairwise_distances = pd.concat(pair_frames, ignore_index=True)
meta_columns = [
    "sample_id",
    "source_id",
    "date_start",
    "date_end",
    "measurement_era",
    "sample_target",
    "countries",
    "pairs",
]
country_distances = pd.DataFrame(
    country_rows,
    columns=meta_columns
    + [
        "country_iso3",
        "country_name",
        "country_label",
        "classified_total_pct",
        "nearest_js_distance",
        "farthest_js_distance",
        "mean_js_distance",
        "peer_countries",
        "automation_conditional_share",
    ],
)
country_influence = pd.DataFrame(
    influence_rows,
    columns=meta_columns
    + [
        "country_iso3",
        "country_name",
        "mean_js_distance",
        "country_mean_js_distance",
        "remaining_countries",
        "leave_one_out_mean_js_distance",
        "leave_one_out_minus_full",
        "status",
    ],
)
window_summary = pd.DataFrame(summary_rows)
mode_dispersion = pd.DataFrame(mode_rows)
numerical_diagnostics = pd.DataFrame(diagnostic_rows)


# Country-level leave-one-out results belong beside the country's distances.
country_distances = country_distances.merge(
    country_influence[
        ["sample_id"]
        + window_key
        + [
            "country_iso3",
            "leave_one_out_mean_js_distance",
            "leave_one_out_minus_full",
        ]
    ],
    on=["sample_id"] + window_key + ["country_iso3"],
    validate="one_to_one",
)
logging.info(
    "Distance diagnostics:\n%s", numerical_diagnostics.to_string(index=False)
)
manifest["review_checks"] = numerical_diagnostics.to_dict(orient="records")
if numerical_diagnostics["flagged"].any():
    raise ValueError(f"{RESULTS_DIR}: unresolved distance checks")
tables = {
    "pairwise_distances": pairwise_distances,
    "country_distances": country_distances,
    "window_summary": window_summary,
    "mode_dispersion": mode_dispersion,
}
for table in tables.values():
    table.insert(0, "run_id", run_id)
    table["design_id"] = np.where(
        table["sample_id"].eq("g20_common_five"),
        "g20_profiles_v1",
        "convergence_v1",
    )
    table["uncertainty"] = "not_estimated"
    table["log_base"] = 2
output_files = write_tables(tables, RESULTS_DIR)
if len(pairwise_distances) >= 100:
    pairwise_distances.to_parquet(OUTPUT_PAIRS_PARQUET, index=False)
    output_files.append(OUTPUT_PAIRS_PARQUET)
logging.info("Windows:\n%s", window_summary.to_string(index=False))
finish_stage(manifest, output_files)
