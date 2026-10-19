# Collaboration measurement register

This register records what the local release documentation establishes and what
remains unresolved. Collection dates and the two comparison sequences follow the
[original research contract](../archive/inspection_workflow_2026_10_16/docs/convergence_analysis_plan.md).
Product labels alone
do not establish identical sampled populations or classifier behavior.

| Window | Documented Claude product label/scope | Measurement and publication caveats |
| --- | --- | --- |
| August 2025 | Free and Pro | Collaboration percentages use the geographic total. The documented 200-conversation country floor is applied in enrichment, not raw preprocessing. |
| November 2025 | Free and Pro | Same documented product label and percentage definition; the enrichment floor does not justify adding a floor to the selected raw aggregates. |
| February 2026 | Free, Pro, and Max | Product label changes within the legacy sequence. The local source includes the previously documented numeric-distribution restoration; its hash identifies that vintage. |
| April 2026 | Claude chat and Cowork, Free/Pro/Max | Calendar-month windows, alpha-3 identifiers, two-decimal rounding, and geography/aggregation publication thresholds. |
| May 2026 | Claude chat and Cowork, Free/Pro/Max | Same June-release documentation as April; a shared release does not establish identical users or sampled conversations. |

Sources: [September documentation](../data/raw/release_2025_09_15/data_documentation.md),
[January documentation](../data/raw/release_2026_01_15/data_documentation.md),
[March documentation](../data/raw/release_2026_03_24/data_documentation.md), and
[June documentation](../data/raw/release_2026_06_26/data_documentation.md).
The [earlier source review](../archive/inspection_workflow_2026_10_16/docs/huggingface_source_review.md) records the February
source revision and prior methodology research. Exact collaboration classifier
versions and a stable classifier calibration are **not established by these local
data dictionaries**. Do not infer measurement invariance from common labels or
treat an undocumented change as absent. Earlier source research already flagged
classifier/product changes; no new classifier validation is supplied here.

The September dictionary defines enriched automation as directive plus feedback
loop, conditional on classifiable collaboration; augmentation uses learning,
task iteration, and validation. The research variables use those groupings in
every window, with explicit names and retained original values. June publishes
automation/augmentation buckets directly but does not fully specify their
denominator relationship to the five pattern percentages. Compare both candidate
scales and report differences; agreement supports a numerical replication, not
proof of measurement equivalence or replication of a report figure.

`none` denotes absence of the attribute in the legacy dictionaries;
`not_classified` can reflect privacy filtering or failed classification. Neither
is silently merged into a five-mode composition. Missing auxiliary labels remain
missing. An observed pattern total sums only published patterns, excludes the
separate buckets, and is labelled accordingly; its gap to 100 is a diagnostic,
not an estimate of an unpublished category. Rounding can affect closure.

The descriptive samples select persistent publication. Equal-country summaries
weight countries equally; the publisher's global aggregate has different weights
and can include countries/users outside those samples. Compare these summaries
without treating their difference as an error or inferring conversation counts.
No source supports conversation-level sampling uncertainty for this project.
