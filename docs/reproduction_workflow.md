# Artificial Practices: source to report

The active pipeline uses one curated profile table and saves only distinct
results consumed by later analysis or reporting. Sample-specific selections,
reshapes and audit checks do not become separate datasets.

```sh
conda activate aei-reproduction
make test
make practices
make verify-practices
```

Use the environment name installed locally; `environment.yml` retains its
reviewed name and package pins. Set `PYTHON=/path/to/python` on make to select
an interpreter. Stage dependencies serialize the build, including under `make -j`.
`make practices-science` stops after sensitivities; the full build also includes
the descriptive OLS appendix, consumer export and report.

## Saved data and results

| Stage | Saved tables | Purpose |
| --- | ---: | --- |
| `01_load_audit.py` | 1 | `native_collaboration`: selected native records with source coverage flags |
| `02_build_profiles.py` | 1 | `profiles`: one row per observed geography/window, with values, shares, coverage and membership flags |
| `03_estimate.py` | 4 | Pair distances, country distances including leave-one-out quantities, window summaries and mode dispersion |
| `04_sensitivity.py` | 8 | Contrasts, ranks, influence contrasts/summary, mode-omission windows/contrasts, country changes and pair changes |
| `04_model_diagnostic.py` | 5 | Coefficients, fit summaries, model comparison, model contrasts and fitted observations |
| `05_export.py` | 1 | One validated `consumer_metrics` interface containing core and G20 results |
| `06_report.py` | 0 | Five figures and the working note, reading saved results directly |

That is **20 distinct tables across the whole pipeline**: one source extraction,
one curated dataset and eighteen analysis/result tables. Stage 1 writes its
table under `data/interim/reproduction/`; the remaining nineteen are under
`results/`. No active stage writes prepared copies under
`data/processed/reproduction/` or republishes earlier tables in core/G20 folders.

Every table gets CSV. Only **pairwise_distances** and **consumer_metrics** also
get Parquet, provided they contain at least 100 rows. All other tables are
CSV-only, including the native extraction and curated profiles. Stage readers
use CSV so small fixtures and full builds have the same interface. `<NA>`
represents a missing value; empty strings and the valid country identifier `NA`
remain distinct.
Readers disable pandas' default missing-value aliases and use round-trip float
parsing. The final Parquet consumer retains its validated Arrow field types.

## One profile table, explicit samples

The [profile-building README](../pipeline/README_build_profiles.md) maps the
variables. The curated table currently has 709 observed geography/window rows:
704 country/windows, including partial publication, and five global aggregates.
Five membership flags select legacy-stable, monthly-stable, common-five,
full-published and G20 common-five samples. G20 is a subset of the same records.

The observed populations remain 90 legacy-stable countries, 114 monthly-stable
countries and 90 common-five countries. Full-publication counts are 95, 103, 100,
114 and 121. Seventeen of the nineteen G20 roster countries have complete
five-mode publication in all five windows. Missing modes stay missing; absent
windows are detected by the required publication counts rather than filled rows.

Each sample's distances are calculated against its own peer population. Filtering
a wider-population mean does not produce a G20 mean. Distances use SciPy's base-2
Jensen–Shannon distance, equally weighted unordered pairs, no self-pairs and the
same ordered five conditional fractions. Country dispersion uses `ddof=0`.
The global aggregate retains the publisher's different weights and population.

August–February is the primary within-sequence comparison, with adjacent legacy
contrasts. April–May is secondary. The G20 August–May extension retains
`secondary_cross_regime`, `measurement_equivalence=not_established` and
`behavioral_change_identified=False`. It does not identify behavioral convergence
under constant measurement. Country deletions and mode omissions have no
confidence level; exact-fit OLS influence quantities remain unavailable. The OLS
projection reproduces balanced-sample contrasts algebraically without independent
confirmation, causal interpretation or inferential standard errors.

## Logging and essential checks

The exact four source CSVs, four release dictionaries and original ISO crosswalk
are locked in [reproduction_sources.json](reproduction_sources.json), excluded
from Git. Loading never downloads or refreshes them. Source fingerprints,
selection counts, source-window definitions and audits are retained in
`logs/run.json`; coverage needed by Stage 2 travels with the native records.

The active build keeps two logging files outside the result folders:

- `logs/practices.log`: one readable log, with a stage prefix on every message.
  It records sample counts, audit findings, diagnostics and written file paths.
- `logs/run.json`: one run record. Python/package versions and the environment
  fingerprint appear once. Each stage records its status, dates, command, seed,
  input/output paths and relevant audit summaries.

Stage 1 starts a fresh log and run record. Subsequent stages append their
messages and update their own entry. A stage must complete before its consumers
start; an interrupted or failed stage remains incomplete. Stage 6 marks the
whole build complete. The files describe the latest execution; preserve a run
explicitly when it needs to become a historical reference.

Raw-source and country-code fingerprints are checked at their points of use.
The loader hashes each raw file once. Intermediate tables and source code are
not hashed or copied into results. Editing a generated table therefore does
not trigger an integrity exception; rerun `make practices` to rebuild the
analysis from the locked sources. Data checks still reject invalid mappings,
duplicate keys, invalid percentages, unsuitable samples and numerical failures.
The final consumer schema and unique grain are validated in Stage 5.

This is also the pattern to reuse in another project: one ordered Makefile,
one shared log, one run record, source fingerprints at ingestion, and explicit
analytical checks in the stages. Keep code and environment definitions in the
repository. `begin_stage(..., new_run=True)` starts the first stage;
`finish_stage(..., complete_run=True)` closes the final stage. The shared
helpers contain logging and file IO, without analytical specifications.

The final consumer has 7,127 rows, including the original 1,310 core rows and
core field types. There is one consumer CSV/Parquet dataset and schema/provenance
JSON; no compatibility dataset or duplicated scientific-table folders. Reporting
reads that interface plus the original saved model observations. Its
[working note](../results/06_report/research_note.md) does not replace
or publish the accepted [research note](../research/research_note.md).

## Historical comparison and archives

`make verify-practices` optionally compares 41 locked historical references:
source records, core/global/G20 profile views, pair/country distances, window
and mode quantities, sensitivities, model results and the original core consumer
rows/schema. It reconstructs old sample views in memory from the flagged profile
table; the analytical pipeline does not recreate the historical file layout.
Scientific values, identities, missingness and statuses are compared at the
reviewed tolerances (`atol=1e-12`, `rtol=1e-10`). Execution IDs, producer labels and
artifact locations can change. A comparison applies to its recorded run IDs.
Its optional report is written to `logs/verification.json`; it is not part of
an ordinary build.

This optional check needs accepted ignored reference bundles under
`archive/inspection_workflow_2026_10_16/results/` and historical prepared inputs
under `data/`. They are not analytical inputs. The raw-to-report build runs
without archived code, results or manual historical run pins.

The [inspection archive](../archive/inspection_workflow_2026_10_16/README.md)
preserves the original workflow, reviews and accepted bundles. The generated
working outputs replaced on 18 October 2026 are preserved separately in
[the output archive](../archive/generated_before_single_table_2026_10_18/README.md).
Historical acceptance claims and reader-facing research files are unchanged.
The per-stage logging files replaced by the shared log are preserved in
[the logging archive](../archive/logging_before_simplification_2026_10_18/README.md).
