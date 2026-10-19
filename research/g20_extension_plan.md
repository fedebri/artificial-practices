# Delegation, learning, and collaboration across observed G20 countries

Exploratory amendment dated 15 October 2026. Design ID: `g20_profiles_v1`.
The user requested and authorized this extension after reviewing the completed
`convergence_v1` study. The original design freeze, estimates, and local release
remain historical records. This amendment adds a country-focused extension;
it does not retroactively change the original primary population or findings.

## Research question and delivery

How do major economies differ in delegating tasks to Claude, learning from it,
and collaborating with it, and how persistent are those differences?

Named country profiles lead the extension. Average convergence is a supporting
summary. Present the five collaboration modes before compressing them into an
automation share or distance statistic. Include every eligible country rather
than selecting only dramatic cases. No G20-specific profile or distance results
have been inspected at this amendment; only saved membership metadata have been
checked. The original broad-sample estimates and sensitivities are prior exposure.
This is exploratory work, not preregistration.

## Population and unchanged measurement

The frame is the 19 country members: Argentina, Australia, Brazil, Canada, China,
France, Germany, India, Indonesia, Italy, Japan, South Korea, Mexico, Russia,
Saudi Arabia, South Africa, Türkiye, the United Kingdom, and the United States.
The European Union and African Union are regional members, not country units.
See the [official membership description](https://www.g20.org.za/about-g20/).
The roster is declared literally in the extension script; no additional download
or dependency is required during execution.

The coverage grid retains all 19 countries and five windows, including absent
members. The analytical population requires a complete valid five-mode profile
in every window. The reviewed Stage 2 metadata indicate 17 qualifying countries,
85 country/window profiles, and 425 mode cells. China and Russia are absent from
the audited country scope. These are expectations to reconcile locally, not
hardcoded acceptance counts or claims of no AI use. Do not impute missing modes
or exclude other countries to preserve those expectations.

Reuse the authoritative Stage 3 profiles from
`20261015T182348870407Z`, selecting only `full_published` before applying the G20
filter. The other sample branches repeat source cells and must not be pooled.
Use Stage 2 membership `20261015T170349582957Z` and Stage 1 window contract
`20261015T165424126402Z`. The accepted Stage 4 manifest
`20261015T183053341322Z` supplies fingerprints for these reviewed inputs.
It is read only as an integrity record, not as an input of country distances.

Original percentages, five-mode totals, conditional shares, native identifiers,
source names, auxiliary labels, and lineage remain intact. Do not normalize again.
Keep all five collection periods visible, with the February–April measurement
break marked and no cross-break contrast. Changing products, classifiers,
publication, users, and window lengths remain limitations. These countries are
not representative of all G20 members, all residents, or economy-wide AI use.

## Increment 1: coverage and country profiles

`pipeline/07_g20_profiles.py`, invoked with `make g20-profiles`, reads only the
explicit reviewed inputs above. The assistant performs static checks; the user
runs the synthetic tests and stage locally. It creates versioned bundles under
`results/07_g20_profiles/<run_id>/` and
`data/processed/07_g20_profiles/<run_id>/`.

Review outputs:

- `membership_coverage`: 19-country × five-window grid, eligibility, stable
  inclusion, source exclusions, and explicit absence reasons.
- `country_summary` and `sample_flow`: eligibility counts and filter losses.
- `country_profiles` and `mode_shares`: unchanged original/conditional variables
  for the stable sample, with new extension and upstream provenance fields.
- `profile_membership_mismatches` and `review_counts`: reconciliation flags.
- `collaboration_profiles.png/pdf`: five snapshots, fixed country order and
  common percentage scale. No clustering or selected-country filtering.
- `country_trajectories.png/pdf`: named-country small multiples with five-mode
  shares, actual date spacing, a marked gap, and automation/coverage annotations.
- `run_manifest.json`, code/doc snapshots, and `stage.log`: hashes, parameters,
  counts, packages, execution status, and the pending review checkpoint.

Charts read the saved review artifacts. No Jensen–Shannon distances, temporal
contrasts, country rankings, selected pair narratives, or regressions are computed
in this increment. Passing execution leaves substantive review pending. Retain
incomplete or flagged runs; do not automatically choose the latest output.

Local handoff:

```bash
make test
make g20-profiles
```

Return the test summary and review-bundle path. Review coverage, denominators,
all country profiles, and figure readability before the next increment. The
first extension run is not a reproduction of the finalized broad-sample note.

## Later increments, after profile review

1. Compare country pairs using the full five-mode profile. Recompute SciPy base-2
   Jensen–Shannon distances within the reviewed G20 population. Existing means
   against 90 or 114 peers cannot be filtered into G20 estimates. Show a labelled
   pairwise matrix and country mean distances, with equal country/pair weights.
2. Describe within-sequence mode changes and persistence. Retain the five-window
   overview, but estimate legacy and monthly contrasts separately. Inspect whether
   common movement masks persistent country differences. Repeat the appropriate
   population, denominator, country-exclusion, and mode-omission checks for this
   population rather than borrowing conclusions from the original study.
3. Choose short country comparisons using recorded descriptive criteria after
   reviewing all countries, such as similar automation shares with contrasting
   five-mode profiles. Record case selection and prior exposure. Do not label
   patterns national cultures or explain them by institutions without evidence.
4. Integrate the reviewed extension into a new note revision from saved `results/`
   artifacts only. Preserve the broad-sample result as context. Add a model only
   if the profile review identifies a question it can usefully answer; no default
   GDP regression, clusters, p-values, or conversation-sampling intervals.

Every later stage will pin the exact reviewed extension run. Further changes in
questions, samples, comparisons, or case-selection rules require a recorded
amendment. Until execution and review, the research note presents this extension
as planned work, with coverage feasibility distinguished from empirical findings.

## Profile checkpoint accepted; pairwise increment prepared

The user reported 75 tests passing in 92.26 seconds and ran Stage 7 as
`20261015T203008038808Z`. The
[profile review](../archive/inspection_workflow_2026_10_16/docs/stage07_g20_review_2026_10_15.md) accepts its 17 countries,
85 profiles, and 425 mode cells for pairwise analysis, under the exact
[review decision and hashes](../archive/inspection_workflow_2026_10_16/docs/g20_profile_review_2026_10_15.json).
Country profiles have now been inspected and their illustrative patterns
recorded as prior exposure. The original amendment above remains historical.

The snapshot heatmap is readable. A trajectory title/legend overlap was found;
its plotting layout is corrected in code, with local visual confirmation still
pending. The note uses the reviewed heatmap, and the original run stays intact.
A later `make g20-profiles` can generate a new figure bundle. Stage 8 remains
pinned to the accepted data from `20261015T203008038808Z`, not that later run.

`pipeline/08_g20_pairwise.py` prepares the next increment for local execution:

```bash
make test
make g20-pairs
```

It exports all within-window G20 pair distances, country mean/nearest/farthest
distances, all nearest-peer ties, five window summaries, and every pair with an
automation gap no greater than 1.0 percentage point. The inclusive boundary has
only a `1e-12`-pp floating-point tolerance. The choice follows profile exposure
and precedes G20 distance inspection. It is a descriptive viewing rule, not an
inferential match. Both five-mode profiles remain in the matched-pair export.

The expected output contains 680 unordered pair/window records and 85 country
distance records, with 16 peers per country. Save the review bundle under
`results/08_g20_pairwise/<run_id>/`; downstream datasets are under
`data/processed/08_g20_pairwise/<run_id>/`. Each run records reviewed input/code
hashes, parameters, diagnostics, counts, versions, and pending review status.
Pair heatmaps use a fixed alphabetical country order and a common color scale
across the five windows. The latest-window country figure shows mean peer
distance and the observed nearest-to-farthest range, without uncertainty bounds.

The assistant has not executed this stage or its ten new synthetic cases.
Review the local test summary, distances, nearest peers, automation-matched pairs,
numerical identity checks, and figures before within-sequence changes or further
sensitivities. No temporal contrasts, model, p-value, or interval is added here.

## Pairwise checkpoint accepted; change/sensitivity increment prepared

The user reported **85 tests passed in 109.04 seconds** and supplied pairwise
run `20261015T210024734414Z`. The
[pairwise review](../archive/inspection_workflow_2026_10_16/docs/stage08_g20_review_2026_10_15.md) accepts 680 pair/window
records and 85 country means, with no numerical flags and readable figures.
The [decision](../archive/inspection_workflow_2026_10_16/docs/g20_pairwise_review_2026_10_15.json) pins seven exact input files
from this run and reviewed profile run `20261015T203008038808Z`.
All snapshot means, nearest peers, and automation-matched pairs are now prior
exposure. The original amendment and earlier checkpoints remain historical.

`pipeline/09_g20_changes.py`, invoked with `make g20-changes`, implements:

- February minus August as the primary endpoint; November minus August and
  February minus November as adjacent legacy contrasts; May minus April as a
  separate secondary contrast. No February–April contrast or fitted trend.
- Country changes in conditional and original mode percentages, automation,
  five-mode coverage, and mean distance to G20 peers. Pair changes retain the
  same unordered pairs at both endpoints, without silently dropping records.
- Window automation means and population standard deviations (`ddof=0`) on
  conditional and original-denominator scales, plus each mode's dispersion.
- Descriptive Spearman persistence of automation country ranks and pair-distance
  ranks. Constant or insufficient ranks remain explicitly unavailable. Shared
  pairs are dependent; no p-values or intervals are computed.
- Excluding each country in turn at both endpoints, then comparing the change
  with the full sample. This measures sensitivity to membership, not causality.
- Omitting each mode and reconditioning the other four, holding membership
  fixed. A country with zero remaining mass makes the whole mode/window
  unavailable; no pseudocount, imputation, or silent country exclusion.
- Comparing common-five, era-stable, and full per-window eligible G20 membership
  using the saved coverage grid. Identical populations are reported as identical
  without repeating estimation. Different populations remain unestimated until
  their profiles are prepared and reviewed.

Country-mean and pair-mean changes must reproduce each aggregate change within
`1e-12`; finite mode-omission distances must lie in the valid range. Review flags
prevent processed export and charts. All estimates remain descriptive, with no
model, resampling, or significance tests. Country changes reflect movement by
the country and its peers; mode omissions alter the metric's geometry.

Versioned outputs under `results/09_g20_changes/<run_id>/`:

| Artifact | Expected rows for the reviewed 17-country sample |
| --- | ---: |
| `window_summary` | 5 |
| `contrasts` | 4 |
| `country_changes` | 68 |
| `pair_changes` | 544 |
| `mode_dispersion` | 25 |
| `rank_persistence` | 8 |
| `country_influence` | 68 |
| `mode_sensitivity_windows` | 25 |
| `mode_sensitivity_contrasts` | 20 |
| `population_comparison` | 15 |
| `numerical_diagnostics` | 4 |
| `review_counts` | 2 |

Each table has CSV and parquet copies with reviewed lineage. Country/pair changes
also export to `data/processed/09_g20_changes/<run_id>/`. Three PNG/PDF figures
show all five snapshot levels with a marked break, endpoint country-distance
changes, and endpoint mode changes. The run records code/input hashes, parameters,
versions, row counts, diagnostics, and pending substantive review status.

Eleven new isolated synthetic cases cover known convergence, a common automation
shift without dispersion, row-order invariance, alternative population coverage,
review/hash gates, missing pairs, duplicate countries, inconsistent aggregates,
and insufficient-country/zero-residual cases. The assistant performs static
checks only. The expected full suite is **96 cases**; local execution is pending.

```bash
make test
make g20-changes
```

Return the test summary and review-bundle path. Review the temporal, country,
mode, denominator, population, and influence outputs before adding conclusions
or finalizing another note revision. No original study result or prior bundle
is overwritten.

## Change/sensitivity checkpoint accepted; reporting integrated

The user reported **96 tests passed in 129.48 seconds** and supplied run
`20261016T063137128771Z`. The
[review](stage09_g20_review_2026_10_16.md) accepts the planned counts, matching
code/input provenance, clear numerical checks, and all three figures under the
[dated decision](../archive/inspection_workflow_2026_10_16/docs/g20_changes_review_2026_10_16.json).

The legacy endpoint distance falls 20.79% and April–May rises 3.34%. Both endpoint
directions survive every single-country and mode exclusion. The first legacy
interval is less stable: Brazil exclusion and directive/learning omissions
reverse its small decline. All alternative G20 populations have identical
membership; they do not supply independent robustness evidence.

Country examples, mode changes, automation summaries, rank persistence, and all
sensitivity exceptions are integrated into a new note revision from saved
results only. Original broad-sample sections and all previous bundles remain
unchanged. Case selection follows complete-result inspection and is exploratory.
No G20 country/window model is added: in this balanced sample its window
contrasts reproduce changes in mean pair distance. The original study's model
already illustrates that identity. There is no independent model confirmation.

No analytical code or test changed at this checkpoint; the current suite remains
96 cases. This reporting amendment is accepted research output, with clean G20
reproduction pending before an additional final release.

## Clean extension replay

Replay the G20 extension from the exact reviewed core Stage 1–4 inputs already
used by Stage 7. The original core study's clean replay is separate evidence;
it does not establish reproduction of the extension. Use the project environment
and repository root, retaining accepted references and all new versioned runs:

```bash
make test
make g20-profiles
```

Return the test summary and new Stage 7 bundle. Review its coverage, profile,
mode, and reconciliation tables against reference `20261015T203008038808Z`,
excluding execution lineage. Check the new trajectory figure visually: its
title/legend layout repair was already present in the reported 96-case suite,
but the 17-country rerender is pending. Figure changes caused by that documented
repair do not permit analytical table changes.

After accepting the new profile run, repin Stage 8 and its isolated fixtures to
that exact run and hashes, record the replay review, then run `make g20-pairs`.
Compare all saved pair, country, nearest-peer, matching, and diagnostic results
against `20261015T210024734414Z`, excluding lineage. Preserve its specifications,
inclusive matching tolerance, country order, and figure scales.

After accepting the new pairwise run, repin Stage 9 and its fixtures to the new
Stage 7/8 runs and hashes, then run `make g20-changes`. Compare all twelve result
tables with `20261016T063137128771Z`, excluding lineage. Require identical
membership, definitions, counts, statuses, and directional sensitivity findings;
use the already recorded `1e-12` tolerance for numerical differences and record
environment versions. Do not relax tolerances or alter design to obtain a match.

Do not run all three targets before these reviews: their literal pins would
otherwise reuse the old accepted inputs and fail to demonstrate a new lineage.
After the complete new chain matches and figures pass review, record its status
and package the final extension note from saved results. Do not claim a raw-data
rerun or an independently reproduced core study from this extension-only replay.

## Profile replay accepted; pairwise replay prepared

The user reported **96 tests passed in 126.98 seconds** and supplied profile
replay `20261016T064844160033Z`. The
[replay review](../archive/inspection_workflow_2026_10_16/docs/stage07_g20_replay_review_2026_10_16.md) and
[decision](../archive/inspection_workflow_2026_10_16/docs/g20_profile_replay_review_2026_10_16.json) accept an exact match of
all seven result tables excluding `run_id`. Inputs, parameters, package versions,
counts, and clear checks match the reference. The unchanged heatmap and repaired
trajectory figure pass visual review; the pending layout check is closed.

Stage 8 and its isolated fixture paths are repinned to this profile run and new
dated decision. All distance, weighting, matching, tie, and figure specifications
remain unchanged; the expected suite remains **96 cases**. Earlier decisions,
accepted bundles, and note revisions remain preserved. The assistant performs
static checks only.

```bash
make test
make g20-pairs
```

Return the test summary and new `results/08_g20_pairwise/<run_id>/` path.
Compare its seven tables and figures against `20261015T210024734414Z`, excluding
execution lineage, before accepting and repinning Stage 9. Stage 9 remains
pinned to the old reference chain until that checkpoint. Only profile-stage
reproduction has been accepted; the full extension replay remains pending.

## Pairwise replay accepted; change/sensitivity replay prepared

The user reported **96 tests passed in 134.93 seconds** and supplied pairwise
replay `20261016T065546839194Z` from profile replay `20261016T064844160033Z`.
The [review](../archive/inspection_workflow_2026_10_16/docs/stage08_g20_replay_review_2026_10_16.md) and
[decision](../archive/inspection_workflow_2026_10_16/docs/g20_pairwise_replay_review_2026_10_16.json) accept an exact match of
all seven tables excluding `run_id` and `stage7_run_id`. Parameters, versions,
counts, diagnostics, nearest peers, and matching selections reproduce. Both PNG
figures are unchanged and pass visual review; PDFs differ only in date metadata.

Stage 9 and its isolated fixture paths are repinned to this exact new chain and
decision. All four contrasts, variables, metric, weights, ranks, sensitivities,
numerical tolerances, and plotting specifications remain unchanged. The expected
suite remains **96 cases**. Earlier decisions, accepted bundles, and note
revisions remain preserved. The assistant performs static checks only.

```bash
make test
make g20-changes
```

Return the test summary and new `results/09_g20_changes/<run_id>/` path. Compare
all twelve tables and three figures against `20261016T063137128771Z`, excluding
execution lineage, before recording complete extension reproduction and
preparing final local packaging. The existing `1e-12` numerical tolerance and
all directional sensitivity conclusions remain fixed. Only profile and pairwise
replay are accepted at this checkpoint; temporal replay and a final extension
release remain pending.

## Complete replay accepted; final local packaging prepared

The user reported **96 tests passed in 133.26 seconds** and supplied change
replay `20261016T070200203468Z`. The
[complete replay review](stage09_g20_replay_review_2026_10_16.md) accepts an exact
match of all twelve tables excluding the three lineage fields. Parameters,
versions, counts, and checks match; all three PNGs are unchanged and PDFs differ
only in date metadata. Together with accepted profile and pairwise replays,
the extension has status `matched_reference_with_new_lineage`, from the exact
reviewed core prepared inputs. No new raw-data or core-study replay is claimed.

A new reviewed note source revision uses the replay lineage and saved artifact
copies. Findings and original broad-sample analytical sections remain unchanged.
Reporting metadata identifies the complete chain; the original release record
is copied locally so links remain usable in a separate extension release folder.
The repaired trajectory figure is available as an optional companion. All
original results, historical decisions, and earlier revisions remain preserved.

`pipeline/10_finalize_g20.py`, invoked with `make g20-finalize`, reads only the
reviewed note source and dated local release decision. It verifies the exact
source inventory, copies all reviewed files to
`results/research_note/g20_profiles_v1/<release_id>/`, changes only note
status/footer, and records source/copy/code hashes, producer IDs, reproduction
scope, and completion status. No metric, model, or chart is recomputed and no
new consumer metric schema is introduced. The copied revision manifest remains
historical source metadata; `release_manifest.json` records final package status.

Three isolated fixture cases verify preserved copies and status changes,
rejection of an unaccepted decision, and rejection of changed source bytes.
The expected suite is **99 cases**. Static checks are performed by the assistant;
local tests, packaging, and final output review remain pending.

```bash
make test
make g20-finalize
```

Return the test summary and release path. Check package hashes, resolved note
links, qualified conclusions, and final status before recording completion of
the local extension release. No publication, commit, or push is performed.
