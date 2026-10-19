# August–May published-profile comparison

Exploratory amendment dated 16 October 2026. Design ID:
`g20_cross_regime_v1`. The user authorizes a secondary August 2025–May 2026
comparison after inspecting the completed G20 analysis and its editorial note.
This changes the earlier exclusion of all cross-regime comparisons for this
new analysis only. Original specifications, results, releases, and within-regime
comparisons remain unchanged.

## Question, prior exposure, and interpretation

Are published collaboration profiles less dispersed in May than in August among
the same observed G20 countries, and how much relative differentiation persists?

The supplied side-chat response quotes a 24.58% decline using previously
inspected window means of 0.083260 and 0.062798. Record that arithmetic claim as
prior exposure. All five window means, country profiles, and within-regime
sensitivities have also been inspected. The new stage must calculate its own
contrast and sensitivity results locally; this amendment is not preregistration.

The estimand is change in **published five-mode profile dispersion across
measurement regimes**, not an identified change in behavior under constant
measurement. Retain August–February as the primary within-regime endpoint and
April–May as the separate monthly comparison. Add no February–April contrast,
continuous trend, regression adjustment, significance test, or bootstrap.

The [measurement register](../docs/measurement_register.md) documents the relevant limits:

- August covers Free/Pro; May covers chat/Cowork across Free/Pro/Max.
- Common mode names do not establish equivalent classifier calibration.
- August covers approximately a week; May covers a calendar month.
- Fixed countries do not imply fixed users, conversations, or activity mixtures.
- Conditional normalization does not remove product, classifier, coverage,
  or user-composition differences.

Country/period intercepts cannot separate these changes from underlying practices.
Country and mode exclusions assess arithmetic sensitivity, not measurement
equivalence or causal attribution. No sensitivity result from the earlier
contrasts is assumed to carry over.

## Inputs and population

Pin the accepted replay chain:

- Profiles: `20261016T064844160033Z`.
- Pairwise results: `20261016T065546839194Z`.
- Accepted local release: `20261016T071919171212Z`.

`g20_cross_regime_inputs_2026_10_16.json` records the exact fingerprints and
authorization for this new stage. Use the same common-five G20 population;
the reviewed empirical sample has 17 countries. Do not load the original full
dataset, remap countries, redefine modes, or substitute a new source vintage.

Select only the August (`2025-08-04`) and May (`2026-05-01`) profiles from the
accepted data. Require identical country and unordered-pair membership at the
endpoints. Preserve original percentages, conditional shares, coverage, and
upstream lineage. Do not pool repeated analytical sample branches.

## Stage 11 specifications

`pipeline/11_g20_cross_regime.py`, via `make g20-cross-regime`, will:

1. Compare the two saved average base-2 Jensen–Shannon distances, reporting
   May minus August and its relative percentage change. Give each distinct
   unordered country pair equal weight; exclude self-comparisons.
2. Export endpoint changes for every country and pair. Retain conditional and
   original mode/automation values and denominator coverage. Also calculate
   each country's own August–May profile distance with SciPy. Label this
   rearrangement measure separately from its change in mean peer distance;
   the latter reflects movement by both the country and its peers.
3. Report conditional and original-denominator automation means and population
   SDs (`ddof=0`), mode dispersion, automation-country rank persistence, and
   pair-distance rank persistence using descriptive Spearman correlations.
4. Exclude each country in turn at both endpoints and recalculate the distance
   contrast. Omit each mode in turn, explicitly recondition the remaining four,
   and calculate both endpoint means and their contrast. Hold membership fixed.
   A zero remaining total makes that mode/window unavailable, without dropping
   the country or adding a pseudocount.
5. Check numerical identities against saved country and pair means, finite
   own-profile distances, and valid mode-omission distances. Keep flagged runs
   for review and withhold processed export/figures if numerical checks fail.

Every table identifies `secondary_cross_regime` and
`published_profiles_across_measurement_regimes`, with measurement equivalence
marked `not_established`. No behavioral effect is identified. Missing/constant
ranks and a zero baseline distance remain explicitly unavailable where relevant.

## Outputs and checkpoint

Versioned outputs use `results/11_g20_cross_regime/<run_id>/` and
`data/processed/11_g20_cross_regime/<run_id>/`. The review bundle contains CSV
and parquet tables, input/code hashes, parameters, versions, status, and logs.

| Table | Expected rows for the reviewed population |
| --- | ---: |
| `window_summary` | 2 |
| `contrasts` | 1 |
| `country_changes` | 17 |
| `pair_changes` | 136 |
| `mode_dispersion` | 10 |
| `rank_persistence` | 2 |
| `country_influence` | 17 |
| `mode_sensitivity_windows` | 10 |
| `mode_sensitivity_contrasts` | 5 |
| `numerical_diagnostics` | 1 |
| `review_counts` | 2 |

Two PNG/PDF figures show every country's change in peer distance alongside its
own profile rearrangement, and all five conditional mode changes. Titles state
the cross-regime scope. No line is drawn through the measurement break.

The assistant writes code and performs static checks only. The user runs tests
and the stage locally. Review compact outputs, figures, sensitivity reversals,
and measurement labels before integrating findings into a new note revision.
Accepted notes and releases are preserved. Integration must replace categorical
claims that all contrasts are within-regime with an explicit distinction between
the main within-regime analyses and this secondary published-profile comparison.

Ten new integration cases reuse the existing isolated source fixture. They cover
known distances and denominator scales, shared own-profile rearrangement without
dispersion, persistent ranks with ties, row ordering, authorization and hash
failures, unmatched pairs, duplicate profiles, missing windows, zero remaining
mass under mode omission, and inconsistent aggregate summaries. The expected
full suite is **109 cases**; no tests or empirical stages are run by the assistant.

```bash
make test
make g20-cross-regime
```

The final interpretation can describe lower or higher published dispersion,
persistent relative positions, and country-specific rearrangement. It must not
attribute the full endpoint change to convergence in underlying practices or
identify a mechanism of social isomorphism.
