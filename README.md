# Artificial Practices

**Applied econometrics / Human–AI collaboration**

Global AI. Convergence in practice?

Do countries' patterns of human–AI collaboration become more similar over time?
This exploratory study uses Anthropic Economic Index aggregates to compare five
collaboration modes across seventeen observed G20 countries and five collection
periods from August 2025 to May 2026. Institutional isomorphism motivates the
question; the analysis measures convergence in published profiles without
identifying imitation, professional norms or coercive pressures.

Read the [research note](research/research_note.md), including the executive
summary, econometric method, country profiles, sensitivities and source definitions.

- Mean pairwise base-2 Jensen–Shannon distance falls **20.79%** over the primary
  August–February comparison and rises **3.34%** over the separate April–May
  comparison.
- Published-profile dispersion is **24.58% lower** in the secondary August–May
  endpoint comparison. It spans product and measurement changes and does not
  identify behavioural convergence under constant measurement.
- The within-sequence G20 findings were reproduced locally. The cross-regime
  extension has one reviewed execution without a separate clean replay.

## Repository contents

| Path | Purpose |
| --- | --- |
| `research/` | The 65-file reader selection: note, figures, directly linked tables, methods and provenance |
| `pipeline/` | Active source-to-report workflow: six stages and a descriptive OLS diagnostic |
| `archive/inspection_workflow_2026_10_16/` | Earlier workflow, tests, notebooks, design/review history and historical results, with an index and checksums |
| `src/` | Shared logging/CSV plumbing (`artifacts.py`) and the optional scientific-equivalence check (`verify_reproduction.py`) |
| `tests/`, `pytest.ini` | Isolated synthetic integration tests |
| `Makefile` | Explicit stage targets and local test command |
| `environment.yml` | Preserved analytical environment, including the reviewed package pins |
| `docs/` | Current workflow guide, measurement register, source information and reproduction locks |
| `data/` | Local source and prepared inputs; excluded from Git |
| `results/` | Current stage outputs, with stage folders directly under this directory; excluded from Git |
| `logs/` | One readable execution log and one run record; optional historical-comparison report, excluded from Git |
| `archive/inspection_workflow_2026_10_16/results/` | Historical runs and accepted note editions; excluded from Git |

`research/` is a reader selection rather than the complete 107-file note edition
or a standalone empirical reproduction package. Its historical manifests describe
their original bundles. The full editions and reviewed runs are preserved under
`archive/inspection_workflow_2026_10_16/results/`; prepared inputs remain in `data/`.
Navigation links in the plan copies are maintained for the current layout;
the historical manifests retain the fingerprints of the archived originals.

The three dated G20 review documents in `research/` support the note's acceptance,
prior-inspection and replay claims. Historical G20 folders under
`archive/inspection_workflow_2026_10_16/results/` supply locked references to the
optional equivalence check. They remain relevant as historical
evidence; the active analytical build writes to `results/`.

## Local development

The active workflow rebuilds the frozen study directly from the locked Anthropic
source files. It does not need historical intermediate runs or manual run-ID edits.
Analytical choices remain explicit in linear scripts; reports read saved results.
Stage 2 writes one curated profile table with sample-membership columns; G20 is
a row selection from it. The whole pipeline saves 20 distinct data/result tables,
including source extraction. Audits stay in `logs/practices.log` and
`logs/run.json`; environment details appear once per build. Only
`pairwise_distances` and `consumer_metrics` also have Parquet copies, at 100 or
more rows; all other tables are CSV-only. Earlier generated
outputs are preserved in the
[18 October output archive](archive/generated_before_single_table_2026_10_18/README.md).

```sh
conda activate aei-reproduction
make test
make practices
make verify-practices
```

Use your existing environment name if it differs. For a fresh environment,
`conda env create --file environment.yml` uses the name declared in that file.
The environment file is unchanged so its reviewed fingerprints remain valid.
`make practices` runs the full study and writes its working edition under
`results/`. Stage targets use the same prefix, for example
`make practices-profiles`. Source fingerprints and analytical checks remain;
intermediate files are no longer checksum-locked. No source snapshots or
per-stage log/manifest files are written into results.
`make verify-practices` additionally needs the accepted local reference bundles
in the archive and their historical prepared data;
it compares 41 historical references, scientific values, unavailable statuses, and the core
consumer schema at the original tolerances. It is optional for a fresh clone.
Its report is saved in `logs/verification.json` with the compared run IDs.
The generated [working note](results/06_report/research_note.md)
does not replace the accepted reader-facing note or publish a release.

See the [current workflow](docs/reproduction_workflow.md) for the stage map,
source requirements, integrity checks, and commands. The
[profile-building README](pipeline/README_build_profiles.md) traces Stage 2's
single table from audited inputs to membership flags using the script's variable names. The
[archive index](archive/inspection_workflow_2026_10_16/README.md) locates the
original scripts, their historical runbook and tests. These preserve the reviewed
intermediate-inspection workflow and explicit historical run pins.

This local checkout includes independent copies of the four required source
release folders and the historical inputs/results. A future public clone needs
the nine source files listed in [the source lock](docs/reproduction_sources.json),
but needs no prepared inputs for `make practices`. See [source data](docs/source_data.md).

## Project separation

Artificial Practices is the active collaboration-convergence project. It was
separated on 16 October 2026 from the earlier Reflexive Diffusion workspace,
which retains its existing Git history, remote, and both development archives.
The new repository has a fresh local Git history and no remote. No initial
commit or publication has been made.

The [separation record](archive/inspection_workflow_2026_10_16/docs/project_separation_2026_10_16.md) identifies the
original workspace, preserved materials and verification. The
[earlier development README](archive/inspection_workflow_2026_10_16/docs/convergence_development_history_before_split_2026_10_16.md)
is retained verbatim as a historical record. The Derver website remains in its
separate `website` project; its public repository link should be changed only
after this project receives an actual public repository URL.

## Data and licensing

Data: [Anthropic Economic Index](https://huggingface.co/datasets/Anthropic/EconomicIndex).
The supplied source documentation identifies CC BY for data and MIT for code.
The project's existing [MIT license](LICENSE) is preserved; it does not replace
the source dataset's attribution or licence terms. Source fingerprints and release
dictionaries accompany the research note and local analytical records.
