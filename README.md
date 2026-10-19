# Artificial Practices

Artificial Practices examines whether countries are becoming more alike in how
they work with AI. It uses published
[Anthropic Economic Index](https://huggingface.co/datasets/Anthropic/EconomicIndex)
aggregates to compare five modes of Claude use—directive, feedback loop,
learning, task iteration and validation—across **17 observed G20 countries**
and five collection periods from **August 2025 to May 2026**.

The analysis measures similarity between countries' full collaboration profiles
using Jensen–Shannon distance, then checks whether the findings survive excluding
individual countries or modes. Average distance falls **20.79% from August to
February**, indicating convergence, and rises **3.34% over April–May**, indicating
renewed differentiation. Both directions survive every exclusion checked.
Country comparisons also show that similar automation shares can conceal very
different mixes of delegation, learning and iteration.

The repository provides a reproducible path from published data to country
profiles, sensitivity checks, figures and a research note. The findings describe
recorded use; they do not establish causes or economy-wide adoption. Changes in
products and measurement require treating August–February and April–May as
separate sequences.

Read the [research note](research/research_note.md) for the full findings,
methods and measurement limits.

## Repository contents

| Path | Purpose |
| --- | --- |
| `research/` | Research note, figures, supporting tables, methods and provenance |
| `pipeline/` | Source-to-report stages and descriptive OLS diagnostic |
| `src/` | Shared logging and file-handling utilities |
| `tests/` | Synthetic integration tests |
| `Makefile`, `environment.yml` | Build commands and pinned analytical environment |
| `docs/` | Workflow guide, source requirements and measurement documentation |
| `data/` | Local source and prepared inputs; excluded from Git |
| `results/` | Generated tables, figures and working note; excluded from Git |
| `logs/` | Execution log and run record; excluded from Git |

## Local reproduction

Place the nine required source files at the paths listed in the
[source lock](docs/reproduction_sources.json); see [source data](docs/source_data.md)
for release details. The pipeline checks their fingerprints and rebuilds from
raw inputs without prepared datasets.

```sh
conda env create --file environment.yml
conda activate aei-econometrics
make test
make practices
```

Skip environment creation if it is already installed. Tests use synthetic data
and can run without the source files. The full build writes tables, figures and
a [working note](results/06_report/research_note.md) to `results/`, with execution
details in `logs/practices.log` and `logs/run.json`.

See the [workflow guide](docs/reproduction_workflow.md) for stage commands and
checks, or the [profile-building guide](pipeline/README_build_profiles.md) for
data-construction details.
