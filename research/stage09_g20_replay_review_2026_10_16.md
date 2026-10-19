# Complete G20 replay review — 16 October 2026

The user reported **96 tests passed in 133.26 seconds** and supplied
`results/09_g20_changes/20261016T070200203468Z`. It uses accepted profile replay
`20261016T064844160033Z` and pairwise replay `20261016T065546839194Z`. Compare
with change/sensitivity reference `20261016T063137128771Z`. The assistant read
compact saved CSV results, manifests, and PNG figures and checked fingerprints.
No test, estimator, empirical stage, or full source dataset was executed or loaded.

## Reproduction checks accepted

All six active code/document hashes match the executed run and saved snapshots
before this checkpoint's documentation updates. All eight input hashes match
their files and the accepted new profile/pairwise chain. Parameters, package
versions, and counts match the reference. Both processed outputs are identical
to their results copies. Each row's `run_id`, `stage7_run_id`, and `stage8_run_id`
identifies the new chain.

All twelve tables match exactly in column order, row order, and values after
excluding only those three lineage fields:

| Table | Rows | Comparison |
| --- | ---: | --- |
| `window_summary` | 5 | Exact |
| `contrasts` | 4 | Exact |
| `country_changes` | 68 | Exact |
| `pair_changes` | 544 | Exact |
| `mode_dispersion` | 25 | Exact |
| `rank_persistence` | 8 | Exact |
| `country_influence` | 68 | Exact |
| `mode_sensitivity_windows` | 25 | Exact |
| `mode_sensitivity_contrasts` | 20 | Exact |
| `population_comparison` | 15 | Exact |
| `numerical_diagnostics` | 4 | Exact |
| `review_counts` | 2 | Exact |

Both review checks remain clear. All three PNG figures are byte-identical to
the reference and pass visual review. The six PNG/PDF outputs match, with PDF
date metadata excluded. No numerical tolerance or design change was needed.

The primary legacy endpoint decline (20.79%), monthly increase (3.34%), country
and mode changes, automation dispersion, rank persistence, population identity,
and all sensitivity exceptions reproduce. In particular, August–November still
reverses under Brazil exclusion and directive/learning omission. There is no
new estimator, inferential claim, case-selection rule, or model.

## Complete extension chain accepted

Together with the dated Stage 7/8 replay reviews, accept reproduction of all
three G20 stages with new lineage, from the exact previously reviewed core
prepared inputs. Record `matched_reference_with_new_lineage` for the extension.
This is not a new raw-data or core-study replay. The original core clean replay
and release remain separate preserved records.

Retain execution manifests with their historical pending-review statuses; this
dated record supplies substantive acceptance. Preserve original references,
decisions, note revisions, raw data, and archives. Refresh the note's G20
lineage and saved copies in a new reviewed revision. All findings and original
broad-sample analytical sections remain unchanged. Include the now-reviewed
trajectory figure as an optional saved companion, not a new analytical result.

## Final local packaging prepared

Under `g20_local_release_decision_2026_10_16.json`, prepare
`pipeline/10_finalize_g20.py` and `make g20-finalize`. This step reads the exact
reviewed note revision and a dated decision, checks its complete file inventory,
copies it to a new versioned local release, and changes only note status/footer.
No dataset is loaded, metric recalculated, chart rendered, or new consumer schema
introduced. Record source/output/code hashes, producer runs, reproduction scope,
and completion status. Keep the source revision's manifest as historical metadata.

Three isolated fixture cases cover packaging, rejection of an unaccepted
decision, and rejection of changed reviewed source bytes. The expected suite
is **99 cases**. The assistant performs static checks only; local packaging and
its output review remain pending.

```bash
make test
make g20-finalize
```

Return the test summary and new
`results/research_note/g20_profiles_v1/<release_id>/` path. Check the final note,
source/copy hashes, and release status before recording completion of the local
extension release. Publication, commits, and pushes are separate actions.
