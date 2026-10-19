# Source data and local execution inputs

The local separation copied the four required release folders independently.
No raw file was altered, no dataset was refreshed, and no CSV was parsed during
the separation. These folders are excluded from Git:

- `data/raw/release_2025_09_15/`
- `data/raw/release_2026_01_15/`
- `data/raw/release_2026_03_24/`
- `data/raw/release_2026_06_26/`

Their required Claude files and dictionaries are declared literally at the top
of `pipeline/01_load_audit.py`. Country mapping in `pipeline/02_build_profiles.py`
reads the supplied ISO crosswalk directly from its original raw release path,
checks its fingerprint against the source lock, and records it as an input.
The upstream repository is
[Anthropic/EconomicIndex](https://huggingface.co/datasets/Anthropic/EconomicIndex).
Preserve the source vintages identified in the saved source inventories; a newer
file with the same name is not automatically an interchangeable input.

Local `data/interim/`, `data/processed/` and `results/` were also copied, including
all pinned reviewed input runs and the complete final note editions. Historical
result folders and note editions have since moved to
`archive/inspection_workflow_2026_10_16/results/`; current outputs remain in
`results/`. The result-archive manifest records original paths and
unchanged file hashes. There are
no symlinks, hard links or runtime dependencies on the old project directory.
A future public clone can now run the [synthesized workflow](reproduction_workflow.md)
from the nine source files in [the source lock](reproduction_sources.json), without
the copied prepared inputs. The
[archived inspection scripts](../archive/inspection_workflow_2026_10_16/README.md)
still require their pinned historical runs. Merely downloading today's upstream files does not
establish identical source bytes. The loader checks the eight Claude/data-dictionary
hashes; profile construction checks the original ISO file and requires the same
source-lock fingerprint recorded by the loader.
These source checks and stage audit summaries are recorded centrally in
`logs/practices.log` and `logs/run.json` when running `make practices`.

Code/fixture tests can run without the empirical datasets. The public reader
material is under `research/`. It contains 65 selected note/evidence files;
navigation links in the plan copies point to current document locations.
Historical release manifests describe the complete original bundles and their
unchanged archived files. Source code licensing is in `LICENSE`; original dataset
licensing and attribution remain governed by the supplied source documentation.
