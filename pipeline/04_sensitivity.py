"""Compare saved distances and alternative specifications within each sample.

Read the one curated profile table plus the four Stage 3 result tables used
here. Sample membership and G20 coverage are row selections of that same data.
The code explicitly declares comparison dates, population rules and roles.

Save eight distinct results under results/04_sensitivity:
contrasts, rank_persistence, influence_contrasts, country_influence_summary,
mode_sensitivity_windows, mode_sensitivity_contrasts, country_changes and
pair_changes. All eight tables are CSV-only.
Identity checks and unestimated comparisons go to logs/practices.log and run.json.

Country deletions remove the same country at both endpoints. Four-mode
sensitivities hold countries fixed; zero remaining mass makes a window
unavailable. These ranges have no confidence level. Cross-regime comparisons
retain their descriptive role without identifying stable-measurement behavior.
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
INPUT_PAIRS = Path("results/03_estimate/pairwise_distances.csv")
INPUT_COUNTRIES = Path("results/03_estimate/country_distances.csv")
INPUT_WINDOWS = Path("results/03_estimate/window_summary.csv")
RESULTS_DIR = Path("results/04_sensitivity")

# Require completed profiles and distances before comparing endpoints.
manifest = begin_stage(
    RESULTS_DIR,
    (
        INPUT_PROFILES,
        INPUT_PAIRS,
        INPUT_COUNTRIES,
        INPUT_WINDOWS,
    ),
    seed=None,  # Deterministic comparisons; no resampling.
    upstream_stages=("02_build_profiles", "03_estimate"),
)
run_id = manifest["run_id"]
profiles = pd.read_csv(
    INPUT_PROFILES,
    keep_default_na=False,
    na_values=["<NA>"],
    float_precision="round_trip",
)
coverage = profiles.loc[profiles["is_g20_country"]]
# Membership is a filter on the same records. These temporary sample views
# supply existing calculations; no sample-specific datasets are saved.
all_profiles = pd.concat(
    [
        profiles.loc[profiles[f"in_{sample_id}"]].assign(sample_id=sample_id)
        for sample_id in (
            "legacy_stable",
            "monthly_stable",
            "common_five",
            "full_published",
            "g20_common_five",
        )
    ],
    ignore_index=True,
)
all_profiles.loc[
    all_profiles["sample_id"].ne("g20_common_five"), "country_label"
] = all_profiles["country_name"]
profiles = all_profiles
all_pairs = pd.read_csv(
    INPUT_PAIRS,
    keep_default_na=False,
    na_values=["<NA>"],
    float_precision="round_trip",
)
all_countries = pd.read_csv(
    INPUT_COUNTRIES,
    keep_default_na=False,
    na_values=["<NA>"],
    float_precision="round_trip",
)
window_summary = pd.read_csv(
    INPUT_WINDOWS,
    keep_default_na=False,
    na_values=["<NA>"],
    float_precision="round_trip",
)
country_influence = all_countries

# Calculate each omission once for every sample/window. A zero remaining
# mass makes the window unavailable rather than changing its population.
sensitivity_rows = []
for window in window_summary.itertuples(index=False):
    group = profiles.loc[
        profiles["sample_id"].eq(window.sample_id)
        & profiles["source_id"].eq(window.source_id)
        & profiles["date_start"].eq(window.date_start)
        & profiles["date_end"].eq(window.date_end)
    ].sort_values("country_iso3")
    matrix = group[
        [
            "conditional_directive_share",
            "conditional_feedback_loop_share",
            "conditional_learning_share",
            "conditional_task_iteration_share",
            "conditional_validation_share",
        ]
    ].to_numpy(dtype=float)
    left, right = np.triu_indices(len(group), k=1)
    for omitted, mode in enumerate(
        (
            "directive",
            "feedback_loop",
            "learning",
            "task_iteration",
            "validation",
        )
    ):
        # Recondition on the remaining four dimensions, holding
        # countries fixed. The resulting distance need not change
        # monotonically on dropping a mode, and the differences are not
        # a decomposition of five-mode JS.
        four_modes = np.delete(matrix, omitted, axis=1)
        remaining_mass = four_modes.sum(axis=1)
        invalid_mass = int(
            (~np.isfinite(remaining_mass) | (remaining_mass <= 0)).sum()
        )
        if invalid_mass:
            # If any country has no remaining mass, the whole window is
            # unavailable; dropping it would change the frozen
            # population.
            estimate = np.nan
            status = "unavailable_zero_remaining_mass"
        elif len(group) < 2:
            estimate = np.nan
            status = "unavailable_fewer_than_two"
        else:
            four_modes = four_modes / remaining_mass[:, None]
            distances = jensenshannon(
                four_modes[left], four_modes[right], base=2, axis=1
            )
            estimate = float(np.mean(distances))
            status = "computed"
        sensitivity_rows.append(
            {
                "sample_id": window.sample_id,
                "source_id": window.source_id,
                "date_start": window.date_start,
                "date_end": window.date_end,
                "measurement_era": window.measurement_era,
                "variant": f"omit_{mode}",
                "omitted_mode": mode,
                "countries": len(group),
                "pairs": len(left),
                "invalid_remaining_mass_profiles": invalid_mass,
                "zero_remaining_mass_countries": invalid_mass,
                "mean_js_distance": estimate,
                "status": status,
                "profile_counts_match": len(group) == window.countries,
                "distance_values_valid": (
                    bool(np.isfinite(estimate) and 0 <= estimate <= 1 + 1e-12)
                    if status == "computed"
                    else None
                ),
                "numerical_flag": status == "computed"
                and not (np.isfinite(estimate) and 0 <= estimate <= 1 + 1e-12),
            }
        )
mode_windows = pd.DataFrame(sensitivity_rows)

# Retain named population alternatives without estimating unreviewed
# samples.
population_rows = []
common_codes = set(
    all_profiles.loc[
        all_profiles["sample_id"].eq("g20_common_five"), "country_iso3"
    ]
)
windows = window_summary.loc[window_summary["sample_id"].eq("g20_common_five")]
for window in windows.itertuples(index=False):
    meta = {
        name: getattr(window, name)
        for name in (
            "source_id",
            "date_start",
            "date_end",
            "measurement_era",
            "sample_id",
            "countries",
        )
    }
    era_dates = set(
        windows.loc[
            windows["measurement_era"].eq(window.measurement_era), "date_start"
        ]
    )
    era_eligible = (
        coverage.loc[
            coverage["date_start"].isin(era_dates)
            & coverage["partition_eligible"].eq(True)
        ]
        .groupby("country_iso3")["date_start"]
        .nunique()
    )
    era_codes = set(era_eligible.loc[era_eligible.eq(len(era_dates))].index)
    per_window_codes = set(
        coverage.loc[
            coverage["date_start"].eq(window.date_start)
            & coverage["partition_eligible"].eq(True),
            "country_iso3",
        ]
    )
    for target, codes in (
        ("common_five", common_codes),
        ("era_stable", era_codes),
        ("full_published", per_window_codes),
    ):
        population_rows.append(
            {
                **meta,
                "target_population": target,
                "target_countries": len(codes),
                "same_as_reviewed_sample": codes == common_codes,
                "additional_country_codes": ",".join(
                    sorted(codes - common_codes)
                ),
                "missing_country_codes": ",".join(
                    sorted(common_codes - codes)
                ),
                "status": (
                    "reviewed_main_sample"
                    if target == "common_five"
                    else (
                        "identical_membership_not_reestimated"
                        if codes == common_codes
                        else "not_estimated_requires_preparation"
                    )
                ),
            }
        )


country_frames = []
pair_frames = []
diagnostic_rows = []
contrast_rows = []
rank_rows = []
influence_frames = []
# Apply the literal comparison dates and roles separately in every sample.
for sample_id in (
    "legacy_stable",
    "monthly_stable",
    "common_five",
    "full_published",
    "g20_common_five",
):
    profiles = all_profiles.loc[all_profiles["sample_id"].eq(sample_id)]
    pairs = all_pairs.loc[all_pairs["sample_id"].eq(sample_id)]
    countries = all_countries.loc[all_countries["sample_id"].eq(sample_id)]
    for contrast_id, start, end in (
        ("legacy_endpoint", "2025-08-04", "2026-02-05"),
        ("legacy_adjacent_1", "2025-08-04", "2025-11-13"),
        ("legacy_adjacent_2", "2025-11-13", "2026-02-05"),
        ("monthly_adjacent", "2026-04-01", "2026-05-01"),
        ("august_may_cross_regime", "2025-08-04", "2026-05-01"),
    ):
        if (
            contrast_id == "august_may_cross_regime"
            and sample_id != "g20_common_five"
        ):
            continue
        if sample_id == "legacy_stable" and contrast_id == "monthly_adjacent":
            continue
        if sample_id == "monthly_stable" and contrast_id != "monthly_adjacent":
            continue
        before = window_summary.loc[
            window_summary["sample_id"].eq(sample_id)
            & window_summary["date_start"].eq(start)
        ].iloc[0]
        after = window_summary.loc[
            window_summary["sample_id"].eq(sample_id)
            & window_summary["date_start"].eq(end)
        ].iloc[0]
        # Rank persistence uses overlapping countries even when
        # full_published window means describe different publication
        # populations.
        shared = profiles.loc[
            profiles["sample_id"].eq(sample_id)
            & profiles["date_start"].eq(start),
            ["country_iso3", "automation_conditional_share"],
        ].merge(
            profiles.loc[
                profiles["sample_id"].eq(sample_id)
                & profiles["date_start"].eq(end),
                ["country_iso3", "automation_conditional_share"],
            ],
            on="country_iso3",
            validate="one_to_one",
            suffixes=("_before", "_after"),
        )
        role = "sensitivity"
        if sample_id == "legacy_stable":
            role = (
                "primary" if contrast_id == "legacy_endpoint" else "adjacent"
            )
        elif sample_id == "monthly_stable":
            role = "secondary"
        if sample_id == "g20_common_five":
            role = {
                "legacy_endpoint": "primary",
                "legacy_adjacent_1": "adjacent",
                "legacy_adjacent_2": "adjacent",
                "monthly_adjacent": "secondary",
                "august_may_cross_regime": "secondary_cross_regime",
            }[contrast_id]
        contrast_meta = {
            "sample_id": sample_id,
            "contrast_id": contrast_id,
            "comparison_id": contrast_id,
            "date_before": start,
            "date_after": end,
            "analysis_role": role,
            "measurement_era": before["measurement_era"],
            "sample_target": before["sample_target"],
            "countries_before": int(before["countries"]),
            "countries_after": int(after["countries"]),
            "countries_shared": len(shared),
            "measurement_era_before": before["measurement_era"],
            "measurement_era_after": after["measurement_era"],
            "design_id": (
                "g20_cross_regime_v1"
                if role == "secondary_cross_regime"
                else (
                    "g20_profiles_v1"
                    if sample_id == "g20_common_five"
                    else "convergence_v1"
                )
            ),
            "estimand": (
                "published_profiles_across_measurement_regimes"
                if role == "secondary_cross_regime"
                else "published_profiles_within_sequence"
            ),
            "measurement_equivalence": "not_established",
            "behavioral_change_identified": False,
        }
        # End minus start: a negative distance/SD change indicates
        # descriptive convergence. These arithmetic differences are not
        # hypothesis tests.
        contrast = dict(contrast_meta)
        for variable in (
            "mean_js_distance",
            "automation_mean_share",
            "automation_sd_share",
            "automation_published_mean_share",
            "automation_published_sd_share",
        ):
            contrast[f"{variable}_before"] = before[variable]
            contrast[f"{variable}_after"] = after[variable]
            contrast[f"{variable}_change"] = after[variable] - before[variable]
        delta = contrast["mean_js_distance_change"]
        available = bool(
            np.isfinite(before["mean_js_distance"])
            and np.isfinite(after["mean_js_distance"])
        )
        contrast["distance_status"] = (
            "computed" if available else "unavailable"
        )
        contrast["relative_distance_change_pct"] = (
            100 * delta / before["mean_js_distance"]
            if available and before["mean_js_distance"] > 0
            else np.nan
        )
        contrast_rows.append(contrast)

        # Remove the same shared country at both endpoints to see
        # whether it drives the contrast, rather than just one window's
        # distance level.
        loo_before = country_influence.loc[
            country_influence["sample_id"].eq(sample_id)
            & country_influence["date_start"].eq(start),
            ["country_iso3", "leave_one_out_mean_js_distance"],
        ]
        loo_after = country_influence.loc[
            country_influence["sample_id"].eq(sample_id)
            & country_influence["date_start"].eq(end),
            ["country_iso3", "leave_one_out_mean_js_distance"],
        ]
        loo = loo_before.merge(
            loo_after,
            on="country_iso3",
            validate="one_to_one",
            suffixes=("_before", "_after"),
        )
        loo["leave_one_out_distance_change"] = (
            loo["leave_one_out_mean_js_distance_after"]
            - loo["leave_one_out_mean_js_distance_before"]
        )
        loo["full_distance_change"] = contrast["mean_js_distance_change"]
        loo["contrast_difference"] = (
            loo["leave_one_out_distance_change"] - loo["full_distance_change"]
        )
        loo["status"] = np.where(
            loo["leave_one_out_distance_change"].notna(),
            "computed",
            "unavailable_fewer_than_two",
        )
        for key, value in contrast_meta.items():
            loo[key] = value
        loo["removed_country_iso3"] = loo["country_iso3"]
        loo = loo.merge(
            profiles[["country_iso3", "country_label"]].drop_duplicates(),
            on="country_iso3",
            validate="one_to_one",
        )
        loo["removed_country_label"] = loo["country_label"]
        loo["remaining_countries"] = int(before["countries"]) - 1
        loo["remaining_pairs_before"] = (
            (int(before["countries"]) - 1)
            * (int(before["countries"]) - 2)
            // 2
        )
        loo["remaining_pairs_after"] = (
            (int(after["countries"]) - 1) * (int(after["countries"]) - 2) // 2
        )
        loo["excluded_distance_change"] = loo["leave_one_out_distance_change"]
        loo["excluded_minus_full"] = loo["contrast_difference"]
        if sample_id == "g20_common_five":
            loo["status"] = np.where(
                loo["excluded_distance_change"].notna(),
                "computed",
                "unavailable",
            )
        influence_frames.append(loo)

        if sample_id == "g20_common_five":
            meta = contrast_meta
            columns = [
                "country_iso3",
                "country_label",
                "classified_total_pct",
                "automation_conditional_share",
                "automation_published_pct",
                "conditional_directive_share",
                "conditional_feedback_loop_share",
                "conditional_learning_share",
                "conditional_task_iteration_share",
                "conditional_validation_share",
                "published_directive_pct",
                "published_feedback_loop_pct",
                "published_learning_pct",
                "published_task_iteration_pct",
                "published_validation_pct",
            ]
            c_before = profiles.loc[profiles["date_start"].eq(start), columns]
            c_after = profiles.loc[
                profiles["date_start"].eq(end), columns
            ].drop(columns="country_label")
            # An outer join enforces identical endpoint country
            # identities; an inner join could silently remove countries
            # and change the reviewed comparison.
            changes = c_before.merge(
                c_after,
                on="country_iso3",
                how="outer",
                validate="one_to_one",
                suffixes=("_before", "_after"),
                indicator=True,
            )
            if changes["_merge"].ne("both").any():
                raise ValueError(
                    f"{contrast_id}: country membership differs at endpoints"
                )
            changes = changes.drop(columns="_merge")
            for date, suffix in ((start, "before"), (end, "after")):
                distance = countries.loc[
                    countries["date_start"].eq(date),
                    ["country_iso3", "mean_js_distance"],
                ].rename(
                    columns={"mean_js_distance": f"mean_js_distance_{suffix}"}
                )
                changes = changes.merge(
                    distance, on="country_iso3", validate="one_to_one"
                )
            changes["mean_js_distance_change"] = (
                changes["mean_js_distance_after"]
                - changes["mean_js_distance_before"]
            )
            # Conditional fractions need a factor of 100 for
            # percentage-point changes; published percentages and
            # classified coverage already use that scale.
            changes["automation_change_pp"] = 100 * (
                changes["automation_conditional_share_after"]
                - changes["automation_conditional_share_before"]
            )
            changes["coverage_change_pp"] = (
                changes["classified_total_pct_after"]
                - changes["classified_total_pct_before"]
            )
            for mode in (
                "directive",
                "feedback_loop",
                "learning",
                "task_iteration",
                "validation",
            ):
                changes[f"{mode}_change_pp"] = 100 * (
                    changes[f"conditional_{mode}_share_after"]
                    - changes[f"conditional_{mode}_share_before"]
                )
                changes[f"{mode}_published_change_pp"] = (
                    changes[f"published_{mode}_pct_after"]
                    - changes[f"published_{mode}_pct_before"]
                )
            changes["automation_published_change_pp"] = (
                changes["automation_published_pct_after"]
                - changes["automation_published_pct_before"]
            )
            changes = changes.assign(**meta)
            country_frames.append(changes)

            p_before = pairs.loc[
                pairs["date_start"].eq(start),
                [
                    "country_i",
                    "country_j",
                    "label_i",
                    "label_j",
                    "js_distance",
                    "automation_gap_pp",
                ],
            ]
            p_after = pairs.loc[
                pairs["date_start"].eq(end),
                [
                    "country_i",
                    "country_j",
                    "js_distance",
                    "automation_gap_pp",
                ],
            ]
            # Pair keys have consistent orientation from Stage 3's
            # country sorting. Every same-pair comparison stays in the
            # fixed peer population.
            pair_changes = p_before.merge(
                p_after,
                on=["country_i", "country_j"],
                how="outer",
                suffixes=("_before", "_after"),
                validate="one_to_one",
                indicator=True,
            )
            if pair_changes["_merge"].ne("both").any():
                raise ValueError(
                    f"{contrast_id}: country pairs differ at endpoints"
                )
            pair_changes = pair_changes.drop(columns="_merge")
            pair_changes["js_distance_change"] = (
                pair_changes["js_distance_after"]
                - pair_changes["js_distance_before"]
            )
            pair_changes = pair_changes.assign(**meta)
            pair_frames.append(pair_changes)
            # With fixed membership, mean individual distance changes
            # and mean pair changes both equal change in the window
            # mean. This is an arithmetic audit, not independent
            # confirmation from three different sources of evidence.

            if contrast_id == "august_may_cross_regime":
                changes["own_profile_js_distance"] = jensenshannon(
                    changes[
                        [
                            "conditional_directive_share_before",
                            "conditional_feedback_loop_share_before",
                            "conditional_learning_share_before",
                            "conditional_task_iteration_share_before",
                            "conditional_validation_share_before",
                        ]
                    ].to_numpy(dtype=float),
                    changes[
                        [
                            "conditional_directive_share_after",
                            "conditional_feedback_loop_share_after",
                            "conditional_learning_share_after",
                            "conditional_task_iteration_share_after",
                            "conditional_validation_share_after",
                        ]
                    ].to_numpy(dtype=float),
                    base=2,
                    axis=1,
                )

            country_error = abs(
                float(changes["mean_js_distance_change"].mean()) - delta
            )
            pair_error = abs(
                float(pair_changes["js_distance_change"].mean()) - delta
            )
            country_before_error = abs(
                float(changes["mean_js_distance_before"].mean())
                - before["mean_js_distance"]
            )
            country_after_error = abs(
                float(changes["mean_js_distance_after"].mean())
                - after["mean_js_distance"]
            )
            pair_before_error = abs(
                float(p_before["js_distance"].mean())
                - before["mean_js_distance"]
            )
            pair_after_error = abs(
                float(p_after["js_distance"].mean())
                - after["mean_js_distance"]
            )
            own_distances = (
                changes["own_profile_js_distance"].to_numpy(dtype=float)
                if contrast_id == "august_may_cross_regime"
                else np.array([], dtype=float)
            )
            own_valid = bool(
                np.isfinite(own_distances).all()
                and (own_distances >= 0).all()
                and (own_distances <= 1 + 1e-12).all()
            )
            diagnostic_rows.append(
                {
                    **meta,
                    "country_mean_change_identity_abs_error": country_error,
                    "pair_mean_change_identity_abs_error": pair_error,
                    "country_before_identity_abs_error": country_before_error,
                    "country_after_identity_abs_error": country_after_error,
                    "pair_before_identity_abs_error": pair_before_error,
                    "pair_after_identity_abs_error": pair_after_error,
                    "own_profile_distance_values_valid": own_valid,
                    "status": "checked" if available else "unavailable",
                    "flagged": not own_valid
                    or (
                        available
                        and not np.allclose(
                            [
                                country_error,
                                pair_error,
                                country_before_error,
                                country_after_error,
                                pair_before_error,
                                pair_after_error,
                            ],
                            0,
                            atol=1e-12,
                            rtol=0,
                        )
                    ),
                }
            )
            # Rank persistence concerns ordering, not distance magnitude
            # or source stability. Pair ranks and country automation
            # ranks answer distinct descriptive questions; a constant
            # endpoint makes rho unavailable rather than zero.

        # Rank persistence shares one calculation across populations.
        # Only G20 also ranks pair distances; core results rank
        # automation alone.
        rank_targets = [
            (
                "automation_share",
                shared["automation_conditional_share_before"],
                shared["automation_conditional_share_after"],
            )
        ]
        if sample_id == "g20_common_five":
            rank_targets.append(
                (
                    "pair_distance",
                    pair_changes["js_distance_before"],
                    pair_changes["js_distance_after"],
                )
            )
        for rank_type, left, right in rank_targets:
            if len(left) < 2:
                correlation = np.nan
                rank_status = "unavailable_fewer_than_two"
            elif left.nunique() < 2 or right.nunique() < 2:
                correlation = np.nan
                rank_status = (
                    "unavailable_constant"
                    if sample_id == "g20_common_five"
                    else "unavailable_constant_automation"
                )
            else:
                correlation = float(left.corr(right, method="spearman"))
                rank_status = "computed"
            rank_rows.append(
                {
                    **contrast_meta,
                    "rank_type": rank_type,
                    "spearman_rho": correlation,
                    "spearman_automation": (
                        correlation
                        if rank_type == "automation_share"
                        else np.nan
                    ),
                    "observations": len(left),
                    "status": rank_status,
                    "ties": "average ranks",
                    "rank_population": (
                        "countries shared by the two windows"
                        if rank_type == "automation_share"
                        else "pairs shared by the two windows"
                    ),
                }
            )

# Assemble the named contrasts while retaining unavailable estimates.
contrasts = pd.DataFrame(contrast_rows)
rank_persistence = pd.DataFrame(rank_rows)
influence_contrasts = pd.concat(influence_frames, ignore_index=True)
# These minima/maxima span deterministic country deletions. They are
# sensitivity ranges, with neither a confidence level nor a
# probabilistic coverage claim.
country_influence_summary = influence_contrasts.groupby(
    [
        "sample_id",
        "contrast_id",
        "date_before",
        "date_after",
        "measurement_era",
    ],
    as_index=False,
).agg(
    checks=("country_iso3", "size"),
    available_checks=("leave_one_out_distance_change", "count"),
    minimum_leaveout_change=("leave_one_out_distance_change", "min"),
    maximum_leaveout_change=("leave_one_out_distance_change", "max"),
)
# Reuse the primary analysis's literal endpoints; a four-mode endpoint
# failure makes its contrast unavailable rather than redefining the
# dates or countries.
mode_contrast_rows = []
for contrast in contrasts.itertuples(index=False):
    for mode in (
        "directive",
        "feedback_loop",
        "learning",
        "task_iteration",
        "validation",
    ):
        sample = mode_windows.loc[
            mode_windows["sample_id"].eq(contrast.sample_id)
            & mode_windows["variant"].eq(f"omit_{mode}")
        ].set_index("date_start")
        before = sample.loc[contrast.date_before]
        after = sample.loc[contrast.date_after]
        computed = (
            before["status"] == "computed" and after["status"] == "computed"
        )
        mode_contrast_rows.append(
            {
                "sample_id": contrast.sample_id,
                "contrast_id": contrast.contrast_id,
                "date_before": contrast.date_before,
                "date_after": contrast.date_after,
                "measurement_era": contrast.measurement_era,
                "variant": f"omit_{mode}",
                "omitted_mode": mode,
                "countries_before": int(before["countries"]),
                "countries_after": int(after["countries"]),
                "mean_js_distance_before": before["mean_js_distance"],
                "mean_js_distance_after": after["mean_js_distance"],
                "status_before": before["status"],
                "status_after": after["status"],
                "mean_js_distance_change": (
                    after["mean_js_distance"] - before["mean_js_distance"]
                    if computed
                    else np.nan
                ),
                "status": "computed" if computed else "unavailable_endpoint",
                "endpoint_statuses": f"{before['status']}; {after['status']}",
            }
        )
mode_contrasts = pd.DataFrame(mode_contrast_rows)

# Attach interpretation fields to contrasts, never infer source
# equivalence from identical country membership or successful numerical
# checks.
contrast_keys = ["sample_id", "contrast_id", "date_before", "date_after"]
mode_contrasts = mode_contrasts.merge(
    contrasts[
        contrast_keys
        + [
            "analysis_role",
            "design_id",
            "measurement_era_before",
            "measurement_era_after",
            "estimand",
            "measurement_equivalence",
            "behavioral_change_identified",
        ]
    ],
    on=contrast_keys,
    validate="many_to_one",
)
mode_windows["flagged"] = mode_windows["numerical_flag"]
# Numerical identities check implementation consistency, not source validity.
diagnostics = pd.DataFrame(diagnostic_rows)
review_counts = pd.DataFrame(
    [
        {
            "check": "temporal_identity_checks",
            "flagged_rows": int(diagnostics["flagged"].sum()),
        },
        {
            "check": "mode_distance_checks",
            "flagged_rows": int(mode_windows["numerical_flag"].sum()),
        },
    ]
)
review_counts["status"] = np.where(
    review_counts["flagged_rows"].gt(0), "review_required", "no_flags"
)
tables = {
    "contrasts": contrasts,
    "rank_persistence": rank_persistence,
    "influence_contrasts": influence_contrasts,
    "country_influence_summary": country_influence_summary,
    "mode_sensitivity_windows": mode_windows,
    "mode_sensitivity_contrasts": mode_contrasts,
    "country_changes": pd.concat(country_frames, ignore_index=True),
    "pair_changes": pd.concat(pair_frames, ignore_index=True),
}
for table in tables.values():
    table.insert(0, "run_id", run_id)
    if "design_id" not in table:
        table["design_id"] = (
            np.where(
                table["sample_id"].eq("g20_common_five"),
                "g20_profiles_v1",
                "convergence_v1",
            )
            if "sample_id" in table
            else "convergence_v1"
        )
    table["uncertainty"] = "not_estimated"
    table["log_base"] = 2
logging.info("Sensitivity checks:\n%s", diagnostics.to_string(index=False))
logging.info(
    "Population comparisons:\n%s",
    pd.DataFrame(population_rows).to_string(index=False),
)
manifest["review_checks"] = review_counts.to_dict(orient="records")
output_files = write_tables(tables, RESULTS_DIR)
if review_counts["flagged_rows"].gt(0).any():
    raise ValueError(f"{RESULTS_DIR}: unresolved sensitivity checks")
logging.info(
    "Contrasts:\n%s",
    contrasts[
        [
            "sample_id",
            "contrast_id",
            "mean_js_distance_change",
            "analysis_role",
        ]
    ].to_string(index=False),
)
finish_stage(manifest, output_files)
