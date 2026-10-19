"""Present saved results as a working note and five figures.

Read only the final consumer CSV and metadata plus saved model observations.
Require both producing stages to be complete. G20 mode shares are selected
from the consumer interface; the report does not need a separate mode-share file,
raw inputs, archived runs or imports of analytical pipeline code.

Plot observed G20 windows, collaboration profiles, country peer-distance changes,
own-profile rearrangement and OLS residuals. Write five PNGs under assets/ and
research_note.md under results/06_report. No data tables are copied.

Keep the measurement break visible. Own-profile distance is rearrangement,
not convergence by itself; leave-one-out ranges are not confidence intervals.
The generated note does not replace or publish an accepted historical edition.
"""

import json
from pathlib import Path

import matplotlib
import pandas as pd

from artifacts import begin_stage, finish_stage

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


INPUT_CONSUMER = Path("results/05_export/consumer_metrics.csv")
INPUT_METADATA = Path("results/05_export/consumer_metadata.json")
INPUT_FITS = Path("results/model_diagnostic/observation_fits.csv")
RESULTS_DIR = Path("results/06_report")
OUTPUT_NOTE = Path("results/06_report/research_note.md")
# Completion requires every declared figure; missing assets stay a failure.
OUTPUT_FIGURES = (
    "g20_evolution.png",
    "collaboration_profiles.png",
    "country_changes.png",
    "own_profile_rearrangement.png",
    "model_residuals.png",
)

# Require completed results; reporting never imports pipeline analysis code.
manifest = begin_stage(
    RESULTS_DIR,
    (
        INPUT_CONSUMER,
        INPUT_METADATA,
        INPUT_FITS,
    ),
    seed=None,  # Presentation is deterministic.
    upstream_stages=("05_export", "model_diagnostic"),
)
# Read presentation inputs and prepare the local figure directory.
report = pd.read_csv(
    INPUT_CONSUMER,
    keep_default_na=False,
    na_values=["<NA>"],
    float_precision="round_trip",
)
metadata = json.loads(INPUT_METADATA.read_text())
modes = report.loc[
    report["table"].eq("g20_mode_shares")
    & report["metric"].eq("conditional_pct")
].rename(columns={"estimate": "conditional_pct"})
fits = pd.read_csv(
    INPUT_FITS,
    keep_default_na=False,
    na_values=["<NA>"],
    float_precision="round_trip",
)
assets = RESULTS_DIR / "assets"
assets.mkdir(parents=True, exist_ok=True)

# Draw within-sequence lines and leave the measurement break visible.
windows = report.loc[
    report["table"].eq("g20_window_summary")
    & report["metric"].eq("mean_js_distance")
].sort_values("date_start")
figure, axis = plt.subplots(figsize=(9, 4), layout="constrained")
for era in ("legacy", "monthly"):
    selected = windows.loc[windows["measurement_era"].eq(era)]
    axis.plot(
        pd.to_datetime(selected["date_start"]),
        selected["estimate"],
        marker="o",
        color="tab:blue",
    )
axis.axvspan(
    pd.Timestamp("2026-02-12"),
    pd.Timestamp("2026-04-01"),
    color="grey",
    alpha=0.15,
)
axis.set_xticks(
    pd.to_datetime(windows["date_start"]),
    windows["date_start"].str.slice(0, 7),
)
axis.set_ylim(bottom=0)
axis.set_ylabel("Mean pairwise JS distance (base 2)")
axis.set_title("Observed G20 profiles; shaded gap marks the measurement break")
axis.grid(axis="y", alpha=0.2)
figure.savefig(assets / "g20_evolution.png", dpi=160)
plt.close(figure)

# Keep country order and color scale fixed across the five profile panels.
country_order = sorted(modes["country_label"].unique())
mode_order = [
    "directive",
    "feedback_loop",
    "learning",
    "task_iteration",
    "validation",
]
dates = sorted(modes["date_start"].unique())
figure, axes = plt.subplots(
    1, len(dates), figsize=(20, 7), sharey=True, layout="constrained"
)
for axis, date in zip(axes, dates, strict=True):
    matrix = (
        modes.loc[modes["date_start"].eq(date)]
        .pivot(index="country_label", columns="mode", values="conditional_pct")
        .reindex(index=country_order, columns=mode_order)
    )
    heatmap = axis.imshow(
        matrix, vmin=0, vmax=100, cmap="Blues", aspect="auto"
    )
    axis.set_xticks(
        range(5),
        [
            "Directive",
            "Feedback loop",
            "Learning",
            "Task iteration",
            "Validation",
        ],
        rotation=60,
        ha="right",
        fontsize=8,
    )
    axis.set_yticks(range(len(country_order)), country_order, fontsize=9)
    axis.set_title(date[:7])
figure.colorbar(heatmap, ax=axes.tolist(), label="Share among five modes (%)")
figure.suptitle("Same observed G20 countries in all five windows")
figure.savefig(assets / "collaboration_profiles.png", dpi=160)
plt.close(figure)

# Label within-sequence and cross-regime peer-distance changes separately.
country_changes = report.loc[
    report["table"].eq("g20_country_changes")
    & report["metric"].eq("mean_js_distance_change")
]
figure, axes = plt.subplots(
    1, 3, figsize=(15, 7), sharex=True, sharey=True, layout="constrained"
)
for axis, contrast, label in zip(
    axes,
    (
        "legacy_endpoint",
        "monthly_adjacent",
        "august_may_cross_regime",
    ),
    ("August–February", "April–May", "August–May: cross-regime"),
    strict=True,
):
    selected = country_changes.loc[country_changes["contrast_id"].eq(contrast)]
    selected = selected.set_index("country_label").reindex(country_order)
    axis.barh(
        country_order,
        selected["estimate"],
        color=[
            "tab:blue" if value < 0 else "tab:orange"
            for value in selected["estimate"]
        ],
    )
    axis.axvline(0, color="black", linewidth=0.8)
    axis.set_title(label)
    axis.set_xlabel("Change in mean distance to peers")
axes[0].invert_yaxis()
figure.suptitle(
    "Negative means closer to peers; both country and peers can move"
)
figure.savefig(assets / "country_changes.png", dpi=160)
plt.close(figure)

# Own-profile rearrangement is a separate display from peer convergence.
own = (
    report.loc[
        report["table"].eq("g20_country_changes")
        & report["metric"].eq("own_profile_js_distance")
    ]
    .set_index("country_label")
    .reindex(country_order)
)
figure, axis = plt.subplots(figsize=(9, 7), layout="constrained")
axis.barh(country_order, own["estimate"], color="tab:purple")
axis.invert_yaxis()
axis.set_xlabel("Distance between own August and May profiles (base 2)")
axis.set_title(
    "Cross-regime rearrangement; this quantity does not measure convergence"
)
figure.savefig(assets / "own_profile_rearrangement.png", dpi=160)
plt.close(figure)

# Present stored OLS residuals without fitting or estimating anything here.
figure, axes = plt.subplots(
    2, 2, figsize=(10, 7), sharex="row", sharey="row", layout="constrained"
)
for row, sample in enumerate(("legacy_stable", "monthly_stable")):
    for column, model in enumerate(("country_only", "country_window")):
        selected = fits.loc[
            fits["sample_id"].eq(sample) & fits["model_id"].eq(model)
        ]
        axis = axes[row, column]
        axis.scatter(
            selected["fitted_distance"], selected["residual"], s=12, alpha=0.6
        )
        axis.axhline(0, color="black", linewidth=0.8)
        axis.set_title(f"{sample}: {model}")
        axis.set_xlabel("Fitted mean peer distance")
        axis.set_ylabel("Residual (JS distance units)")
figure.suptitle("Descriptive projection appendix; no inference")
figure.savefig(assets / "model_residuals.png", dpi=160)
plt.close(figure)

# Build the note from exported metrics, keeping roles and missing statuses.
contrasts = report.loc[report["table"].eq("g20_contrasts")].pivot(
    index=["contrast_id", "analysis_role"], columns="metric", values="estimate"
)
note = [
    "# Artificial Practices: convergence in collaboration profiles",
    "",
    "**Working reproduction of the frozen exploratory study.**",
    "",
    (
        "Do countries’ recorded human–AI collaboration "
        "profiles become more similar?"
    ),
    (
        "The study compares five Anthropic Economic Index "
        "collaboration modes among"
    ),
    (
        f"{len(country_order)} consistently observed G20 "
        "countries in five windows."
    ),
    (
        "Institutional isomorphism motivates the question; "
        "these aggregates do not"
    ),
    "identify imitation, professional norms, coercion or individual learning.",
    "",
    "## Main comparisons",
    "",
    (
        "| Comparison | Role | Initial distance | Final "
        "distance | Change | Relative change |"
    ),
    "| --- | --- | ---: | ---: | ---: | ---: |",
]
for contrast, label in (
    ("legacy_endpoint", "August–February"),
    ("monthly_adjacent", "April–May"),
    ("august_may_cross_regime", "August–May across regimes"),
):
    row = contrasts.loc[contrast].iloc[0]
    role = contrasts.loc[contrast].index[0]
    relative = row["relative_distance_change_pct"]
    relative_text = (
        f"{relative:+.2f}%" if pd.notna(relative) else "unavailable"
    )
    note.append(
        f"| {label} | {role} | {row['mean_js_distance_before']:.6f} | "
        f"{row['mean_js_distance_after']:.6f} | "
        f"{row['mean_js_distance_change']:+.6f} | {relative_text} |"
    )
note.extend(
    [
        "",
        (
            "A negative change describes greater similarity "
            "among published profiles."
        ),
        (
            "August–May spans changed products and "
            "measurement; it does not identify"
        ),
        (
            "behavioral convergence under constant "
            "measurement. The two within-sequence"
        ),
        "comparisons retain their primary and secondary roles.",
        "",
        "![Five observed windows](assets/g20_evolution.png)",
        "",
        "## Population, denominators and distance",
        "",
        (
            "Original Anthropic aggregates are loaded "
            "unchanged. Country identifiers are"
        ),
        (
            "mapped with the supplied ISO crosswalk; six "
            "February rows labelled NONE"
        ),
        "remain in the source audit and are quarantined from country samples.",
        (
            "The G20 country roster has 19 members; only those "
            "with all five modes"
        ),
        (
            "published in every window enter the stable "
            "comparison. Missing rows are"
        ),
        (
            "not inferred to be zero. Persistent publication "
            "selects the population."
        ),
        "",
        (
            "For each country/window, divide the five "
            "published percentages by their"
        ),
        (
            "sum. These conditional fractions retain the "
            "ratios among classified modes"
        ),
        (
            "while excluding none/unclassified mass. Original "
            "percentages and coverage"
        ),
        (
            "remain in the exported evidence. Automation "
            "combines directive and feedback loop."
        ),
        "",
        (
            "Compute SciPy’s base-2 Jensen–Shannon distance, "
            "the square root of divergence,"
        ),
        (
            "for every distinct unordered country pair. Equal "
            "pair weights represent"
        ),
        (
            "countries equally; self-pairs are excluded. G20 "
            "distances use G20 peers."
        ),
        "",
        "![Country compositions](assets/collaboration_profiles.png)",
        "",
        "## Country detail",
        "",
        (
            "A country’s mean peer-distance change reflects "
            "its own movements and those"
        ),
        (
            "of its peers. Own-profile endpoint distance is "
            "instead a nonnegative measure"
        ),
        (
            "of rearrangement; it cannot alone establish "
            "convergence toward other countries."
        ),
        "",
        "![Peer-distance changes](assets/country_changes.png)",
        "",
        (
            "![Own-profile endpoint distance](assets/"
            "own_profile_rearrangement.png)"
        ),
        "",
        "## Sensitivities",
        "",
        (
            "| Omitted mode | August–February | April–May | "
            "August–May across regimes |"
        ),
        "| --- | ---: | ---: | ---: |",
    ]
)
# Read the saved omitted-mode comparisons into the sensitivity table.
omissions = report.loc[
    report["table"].eq("g20_mode_sensitivity_contrasts")
    & report["metric"].eq("mean_js_distance_change")
].pivot(index="omitted_mode", columns="contrast_id", values="estimate")
for mode in mode_order:
    cells = [
        f"{value:+.6f}" if pd.notna(value) else "unavailable"
        for value in omissions.loc[
            mode,
            [
                "legacy_endpoint",
                "monthly_adjacent",
                "august_may_cross_regime",
            ],
        ]
    ]
    note.append(
        f"| {mode.replace('_', ' ').capitalize()} | {' | '.join(cells)} |"
    )
note.extend(
    [
        "",
        (
            "Each omission reconditions the remaining four "
            "modes on fixed membership."
        ),
        (
            "Zero remaining mass makes the window unavailable. "
            "Changed signs qualify"
        ),
        (
            "claims across dimensions; they do not identify "
            "causal mode contributions."
        ),
        (
            "Country deletions remove the same country at both "
            "endpoints. Their ranges"
        ),
        "are deterministic influence diagnostics, not confidence intervals.",
        (
            "The wider-country analyses, published-denominator "
            "alternatives, automation"
        ),
        (
            "dispersion (ddof=0), rank persistence and "
            "population audits remain exported."
        ),
        "",
        "## Descriptive OLS appendix",
        "",
        (
            "Country intercepts describe persistent "
            "peer-distance differences. Adding"
        ),
        (
            "categorical window effects in the balanced legacy "
            "and monthly populations"
        ),
        (
            "reproduces their direct mean-distance changes "
            "algebraically. This provides"
        ),
        (
            "a decomposition and residual diagnostics, with no "
            "independent confirmation"
        ),
        (
            "or causal interpretation. No standard errors or "
            "p-values are exported."
        ),
        "",
        "![Projection residuals](assets/model_residuals.png)",
        "",
        "## Measurement and reproduction",
        "",
        (
            "These are original published aggregates, not "
            "conversation microdata or"
        ),
        (
            "representative samples of residents, workers or "
            "national AI adoption."
        ),
        (
            "Products, classifiers, publication thresholds and "
            "participating users can"
        ),
        (
            "change even with fixed countries. The publisher’s "
            "global aggregate also"
        ),
        (
            "differs from equal-country means in weighting and "
            "population support."
        ),
        "Pairs share countries, and the public aggregates lack the sampling",
        (
            "covariances needed for conversation-level "
            "uncertainty. No inferential"
        ),
        "intervals or hypothesis tests are claimed.",
        "",
        "[Scientific consumer data](../05_export/consumer_metrics.csv) ·",
        "[Units and schema](../05_export/consumer_schema.json) ·",
        (
            "[Source fingerprints and producer runs](../"
            "05_export/consumer_metadata.json) ·"
        ),
        "Optional reference comparison: `logs/verification.json`,",
        (
            "written by `make verify-practices` when local "
            "references are available."
        ),
        "",
        (
            "Data: [Anthropic Economic Index](https://"
            "huggingface.co/datasets/Anthropic/EconomicIndex)."
        ),
        (
            "Data attribution and licensing follow the "
            "supplied source documentation."
        ),
        (
            "Historical accepted notes and review decisions "
            "retain their original status."
        ),
        (
            "This generated working note does not publish or "
            "finalize a new release."
        ),
        "",
        f"Consumer export run: `{metadata['run_id']}`.",
    ]
)
# Record the note and all expected PNG assets as this stage's outputs.
OUTPUT_NOTE.write_text("\n".join(note) + "\n")
finish_stage(
    manifest,
    [OUTPUT_NOTE, *[assets / name for name in OUTPUT_FIGURES]],
    complete_run=True,
)
