"""Fit the descriptive country/window OLS appendix to saved country distances.

Read country_distances and window_summary from Stage 3, plus Stage 4 contrasts.
Use the balanced legacy and monthly samples separately. Country-only and
country/window projections reproduce direct contrasts algebraically; they
provide no independent confirmation, causal interpretation or inferential SEs.

Save five results under results/model_diagnostic: coefficients,
fit_summary, model_comparison, model_contrasts and observation_fits, all CSV-only.
Panel checks, numerical identities and invalid records go to logs/practices.log
and logs/run.json.
Exact fits retain unavailable studentization and Cook's-distance statuses.
"""

import logging
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from artifacts import (
    begin_stage,
    finish_stage,
    write_tables,
)


INPUT_DISTANCES = Path("results/03_estimate/country_distances.csv")
INPUT_WINDOWS = Path("results/03_estimate/window_summary.csv")
INPUT_CONTRASTS = Path("results/04_sensitivity/contrasts.csv")
RESULTS_DIR = Path("results/model_diagnostic")

# Require completed distances and contrasts before preparing the OLS panels.
manifest = begin_stage(
    RESULTS_DIR,
    (
        INPUT_DISTANCES,
        INPUT_WINDOWS,
        INPUT_CONTRASTS,
    ),
    seed=None,  # Deterministic least-squares projections.
    upstream_stages=("03_estimate", "04_sensitivity"),
)
run_id = manifest["run_id"]
distances = pd.read_csv(
    INPUT_DISTANCES,
    keep_default_na=False,
    na_values=["<NA>"],
    float_precision="round_trip",
).rename(columns={"run_id": "stage4_run_id"})
# Only balanced within-regime populations support the window-effect
# identity. A changing full_published population would conflate time and
# country mix.
selected = distances.loc[
    distances["sample_id"].isin(
        [
            "legacy_stable",
            "monthly_stable",
        ]
    )
].copy()
logging.info(
    "Stable model sample filter: %d -> %d rows", len(distances), len(selected)
)
direct_windows = pd.read_csv(
    INPUT_WINDOWS,
    keep_default_na=False,
    na_values=["<NA>"],
    float_precision="round_trip",
)
direct_contrasts = pd.read_csv(
    INPUT_CONTRASTS,
    keep_default_na=False,
    na_values=["<NA>"],
    float_precision="round_trip",
)
# Audit every expected country/window cell before fitting either projection.
panels = []
balance_frames = []
scope_rows = []
for sample_id in ("legacy_stable", "monthly_stable"):
    panel = selected.loc[selected["sample_id"].eq(sample_id)].copy()
    if sample_id == "legacy_stable":
        panel["window_label"] = pd.Categorical(
            panel["date_start"],
            categories=["2025-08-04", "2025-11-13", "2026-02-05"],
            ordered=True,
        )
    else:
        panel["window_label"] = pd.Categorical(
            panel["date_start"],
            categories=["2026-04-01", "2026-05-01"],
            ordered=True,
        )
    # Require every country/window cell exactly once, including the
    # literal expected dates. Equal counts alone would not detect a
    # missing/replaced cell.
    grid = (
        panel[["country_iso3"]]
        .drop_duplicates()
        .merge(
            pd.DataFrame({"date_start": panel["window_label"].cat.categories}),
            how="cross",
        )
    )
    grid["sample_id"] = sample_id
    balance = grid.merge(
        panel[["sample_id", "country_iso3", "date_start"]],
        on=["sample_id", "country_iso3", "date_start"],
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    balance["cell_present"] = balance["_merge"].eq("both")
    balance_frames.append(balance)
    scope_rows.append(
        {
            "sample_id": sample_id,
            "countries": panel["country_iso3"].nunique(),
            "required_windows": len(panel["window_label"].cat.categories),
            "observed_rows": len(panel),
            "enough_countries": panel["country_iso3"].nunique() >= 2,
        }
    )
    panels.append(panel.sort_values(["country_iso3", "window_label"]))
panel_balance = pd.concat(balance_frames, ignore_index=True)
scope_checks = pd.DataFrame(scope_rows)
sample_counts = direct_windows.loc[
    direct_windows["sample_id"].isin(
        [
            "legacy_stable",
            "monthly_stable",
        ]
    ),
    ["sample_id", "date_start", "countries"],
].merge(
    selected.groupby(["sample_id", "date_start"])
    .size()
    .rename("observed_countries")
    .reset_index(),
    on=["sample_id", "date_start"],
    how="outer",
    validate="one_to_one",
)
sample_counts["counts_match"] = sample_counts["observed_countries"].eq(
    sample_counts["countries"]
)
invalid_outcomes = selected.loc[
    ~np.isfinite(selected["mean_js_distance"])
    | ~selected["mean_js_distance"].between(0, 1)
].copy()
review_counts = pd.DataFrame(
    [
        {
            "check": "panel_balance",
            "flagged_rows": int((~panel_balance["cell_present"]).sum()),
        },
        {
            "check": "sample_counts",
            "flagged_rows": int((~sample_counts["counts_match"]).sum()),
        },
        {"check": "invalid_outcomes", "flagged_rows": len(invalid_outcomes)},
        {
            "check": "insufficient_countries",
            "flagged_rows": int((~scope_checks["enough_countries"]).sum()),
        },
    ]
)
logging.info("Model input checks:\n%s", review_counts.to_string(index=False))
if review_counts["flagged_rows"].gt(0).any():
    logging.error("Panel balance:\n%s", panel_balance.to_string(index=False))
    logging.error(
        "Invalid outcomes:\n%s", invalid_outcomes.to_string(index=False)
    )
    raise ValueError(f"{RESULTS_DIR}: unbalanced or invalid model input")

# Collect comparable fit, coefficient and influence records for both panels.
coefficient_rows = []
fit_rows = []
comparison_rows = []
effect_rows = []
contrast_rows = []
observation_frames = []
diagnostic_rows = []
for panel in panels:
    sample_id = panel["sample_id"].iloc[0]
    reference = panel["window_label"].cat.categories[0]
    logging.info(
        "Fitting %s; %d balanced country/window rows", sample_id, len(panel)
    )
    # "0 + C(country_iso3)" supplies one intercept per country without
    # adding a redundant global intercept. The extension adds T-1 date
    # indicators, with the first categorical date as reference; it is
    # not a treatment effect model.
    baseline = smf.ols(
        "mean_js_distance ~ 0 + C(country_iso3)",
        data=panel,
        missing="raise",
    ).fit()
    extension = smf.ols(
        "mean_js_distance ~ 0 + C(country_iso3) + C(window_label)",
        data=panel,
        missing="raise",
    ).fit()
    # OLS is an in-sample linear projection of a bounded distance
    # outcome; fitted values need not themselves lie in [0, 1], so their
    # range is reported below.
    outcome_varies = panel["mean_js_distance"].nunique() > 1
    for model_id, fitted in (
        ("country_only", baseline),
        ("country_window", extension),
    ):
        exact_fit = bool(np.allclose(fitted.resid, 0, atol=1e-12, rtol=0))
        # Leverage depends on the design matrix; Cook's distance also
        # uses the fitted residual scale. These flag descriptive
        # sensitivity, not a calibrated outlier test under independent
        # country/window errors.
        influence = fitted.get_influence()
        observations = panel[
            [
                "sample_id",
                "country_iso3",
                "country_name",
                "source_id",
                "date_start",
                "date_end",
                "measurement_era",
                "mean_js_distance",
            ]
        ].copy()
        observations["model_id"] = model_id
        observations["fitted_distance"] = np.asarray(fitted.fittedvalues)
        observations["residual"] = np.asarray(fitted.resid)
        observations["residual_squared"] = np.square(fitted.resid.to_numpy())
        observations["leverage"] = influence.hat_matrix_diag
        if exact_fit:
            # With no residual scale, studentization and Cook's distance
            # are undefined. Preserve that status instead of reporting
            # spurious zeros.
            observations["standardized_residual"] = np.nan
            observations["cooks_distance"] = np.nan
            observations["influence_status"] = "unavailable_exact_fit"
        else:
            observations["standardized_residual"] = (
                influence.resid_studentized_internal
            )
            # Retain the statistic without exporting its tail
            # probability.
            observations["cooks_distance"] = influence.cooks_distance[0]
            observations["influence_status"] = "computed_descriptive"
        observation_frames.append(observations)
        # A rank-deficient design would make coefficient interpretation
        # ambiguous even if a numerical least-squares solution were
        # returned by the package.
        rank = int(fitted.model.rank)
        parameters = len(fitted.params)
        fit_rows.append(
            {
                "sample_id": sample_id,
                "model_id": model_id,
                "specification": fitted.model.formula,
                "reference_window": reference,
                "observations": int(fitted.nobs),
                "countries": panel["country_iso3"].nunique(),
                "windows": len(panel["window_label"].cat.categories),
                "parameters": parameters,
                "rank": rank,
                "residual_df": int(fitted.df_resid),
                "condition_number": float(fitted.condition_number),
                "sse": float(fitted.ssr),
                "rmse": float(np.sqrt(np.mean(np.square(fitted.resid)))),
                "r_squared": (
                    float(fitted.rsquared) if outcome_varies else np.nan
                ),
                "r_squared_definition": (
                    "centered" if fitted.model.k_constant else "uncentered"
                ),
                "r_squared_status": (
                    "computed"
                    if outcome_varies
                    else "unavailable_constant_outcome"
                ),
                "exact_fit": exact_fit,
                "minimum_fitted_distance": float(fitted.fittedvalues.min()),
                "maximum_fitted_distance": float(fitted.fittedvalues.max()),
            }
        )
        diagnostic_rows.append(
            {
                "sample_id": sample_id,
                "check": f"{model_id}_fit",
                "flagged": rank != parameters
                or not (
                    np.isfinite(fitted.params).all()
                    and np.isfinite(fitted.resid).all()
                    and np.isfinite(fitted.condition_number)
                ),
            }
        )
        for term, estimate in fitted.params.items():
            coefficient_rows.append(
                {
                    "sample_id": sample_id,
                    "model_id": model_id,
                    "term": term,
                    "parameter_type": (
                        "window_effect"
                        if term.startswith("C(window_label)")
                        else "country_intercept"
                    ),
                    "estimate": float(estimate),
                    "units": "base-2 JS distance",
                    "reference_window": reference,
                }
            )
    # Nested models cannot increase minimized SSE. Its reduction
    # describes how much within-country variation the common window
    # shifts account for; this is training-sample fit, not forecast
    # accuracy or a causal explained share.
    baseline_exact = np.allclose(baseline.resid, 0, atol=1e-12, rtol=0)
    comparison_rows.append(
        {
            "sample_id": sample_id,
            "baseline_sse": float(baseline.ssr),
            "country_window_sse": float(extension.ssr),
            "sse_reduction": float(baseline.ssr - extension.ssr),
            "within_country_sse_explained": (
                float(1 - extension.ssr / baseline.ssr)
                if not baseline_exact
                else np.nan
            ),
            "within_country_sse_status": (
                "computed"
                if not baseline_exact
                else "unavailable_baseline_exact_fit"
            ),
            "interpretation": (
                "common-window fit; not independent confirmation"
            ),
        }
    )
    diagnostic_rows.append(
        {
            "sample_id": sample_id,
            "check": "nested_fit_sse",
            "flagged": bool(extension.ssr > baseline.ssr + 1e-12),
        }
    )
    for date in panel["window_label"].cat.categories:
        # Check both algebraic links: country means equal pairwise
        # means, and categorical effects equal changes in those means
        # from the reference.
        effect = (
            0.0
            if date == reference
            else float(extension.params[f"C(window_label)[T.{date}]"])
        )
        direct = direct_windows.loc[
            direct_windows["sample_id"].eq(sample_id)
            & direct_windows["date_start"].eq(date),
            "mean_js_distance",
        ].iloc[0]
        direct_reference = direct_windows.loc[
            direct_windows["sample_id"].eq(sample_id)
            & direct_windows["date_start"].eq(reference),
            "mean_js_distance",
        ].iloc[0]
        country_mean = panel.loc[
            panel["date_start"].eq(date), "mean_js_distance"
        ].mean()
        effect_error = abs(effect - (direct - direct_reference))
        level_error = abs(country_mean - direct)
        effect_rows.append(
            {
                "sample_id": sample_id,
                "date_start": date,
                "reference_window": reference,
                "is_reference": date == reference,
                "window_effect": effect,
                "direct_mean_js_distance": direct,
                "direct_change_from_reference": direct - direct_reference,
                "country_pair_mean_abs_error": level_error,
                "window_effect_abs_error": effect_error,
            }
        )
        diagnostic_rows.append(
            {
                "sample_id": sample_id,
                "check": f"window_identity_{date}",
                "flagged": not (
                    np.isclose(effect_error, 0, atol=1e-10, rtol=0)
                    and np.isclose(level_error, 0, atol=1e-10, rtol=0)
                ),
            }
        )

# Assemble the completed fits before reconciling their temporal contrasts.
coefficients = pd.DataFrame(coefficient_rows)
fit_summary = pd.DataFrame(fit_rows)
model_comparison = pd.DataFrame(comparison_rows)
window_effects = pd.DataFrame(effect_rows)
# Differencing window effects also reproduces adjacent comparisons whose
# first date is not the model's reference. This checks implementation
# consistency.
for direct in direct_contrasts.loc[
    direct_contrasts["sample_id"].isin(
        [
            "legacy_stable",
            "monthly_stable",
        ]
    )
].itertuples(index=False):
    effects = window_effects.loc[
        window_effects["sample_id"].eq(direct.sample_id)
    ].set_index("date_start")["window_effect"]
    change = effects[direct.date_after] - effects[direct.date_before]
    error = abs(change - direct.mean_js_distance_change)
    contrast_rows.append(
        {
            "sample_id": direct.sample_id,
            "contrast_id": direct.contrast_id,
            "analysis_role": direct.analysis_role,
            "date_before": direct.date_before,
            "date_after": direct.date_after,
            "model_window_contrast": change,
            "direct_distance_change": direct.mean_js_distance_change,
            "absolute_error": error,
            "independent_confirmation": False,
        }
    )
    diagnostic_rows.append(
        {
            "sample_id": direct.sample_id,
            "check": f"contrast_identity_{direct.contrast_id}",
            "flagged": not np.isclose(error, 0, atol=1e-10, rtol=0),
        }
    )
model_contrasts = pd.DataFrame(contrast_rows)
observation_fits = pd.concat(observation_frames, ignore_index=True)
# Residual summaries show where the common-shift approximation leaves
# country heterogeneity. They do not estimate individual learning or
# sampling precision.
numerical_diagnostics = pd.DataFrame(diagnostic_rows)
review_counts = pd.concat(
    [
        review_counts,
        pd.DataFrame(
            [
                {
                    "check": "numerical_model_flags",
                    "flagged_rows": int(
                        numerical_diagnostics["flagged"].sum()
                    ),
                }
            ]
        ),
    ],
    ignore_index=True,
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
logging.info("Model checks:\n%s", numerical_diagnostics.to_string(index=False))
manifest["review_checks"] = review_counts.to_dict(orient="records")
if numerical_diagnostics["flagged"].any():
    raise ValueError(f"{RESULTS_DIR}: unresolved model diagnostics")
tables = {
    "coefficients": coefficients,
    "fit_summary": fit_summary,
    "model_comparison": model_comparison,
    "model_contrasts": model_contrasts,
    "observation_fits": observation_fits,
}
for table in tables.values():
    table.insert(0, "run_id", run_id)
    table["design_id"] = "convergence_v1"
    table["uncertainty"] = "not_estimated"
output_files = write_tables(tables, RESULTS_DIR)
logging.info("Model contrasts:\n%s", model_contrasts.to_string(index=False))
finish_stage(manifest, output_files)
