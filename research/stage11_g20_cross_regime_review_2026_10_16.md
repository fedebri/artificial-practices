# Stage 11: August–May published-profile review

Reviewed on 16 October 2026: `20261016T085052724030Z`, design
`g20_cross_regime_v1`. The user reports **109 tests passed in 142.65 seconds**
and ran the empirical stage locally. The assistant reviewed saved CSV tables,
the manifest, provenance snapshots, and both PNG figures; no pipeline, tests,
or estimator was executed by the assistant.

## Decision and scope

Accept for **qualified exploratory reporting of published-profile change**
and integrate into a new note edition. Measurement equivalence remains
unestablished; constant-measurement behavioral change is not identified.
August–February remains primary, April–May remains a separate monthly
comparison, and no February–April contrast or continuous trend is added.
The earlier releases and all within-regime results remain preserved.

The execution manifest's pending review status remains its original record.
This dated decision records the subsequent review. Stage 11 has one reviewed
local execution; a separate clean replay of this extension has **not** been
performed. Earlier reproduction evidence covers the original study and
within-regime G20 extension only. This is acceptance for reporting, not a new
claim of clean reproduction or public release.

## Verification

- All seven pinned producer/release input fingerprints match; the authorization
  record also matches its executed fingerprint.
- All six executed code/document fingerprints match both current files and
  bundled provenance snapshots.
- All eleven table counts match: 2 window summaries, 1 contrast, 17 country
  changes, 136 pair changes, 10 mode-dispersion rows, 2 rank summaries,
  17 country exclusions, 10 omitted-mode window estimates, 5 mode contrasts,
  1 numerical-diagnostic row, and 2 review checks.
- Every table carries the secondary cross-regime role, published-profile
  estimand, unestablished measurement equivalence, and no behavioral
  identification. There are no flagged records. The largest recorded numerical
  identity error is 1.04e-17, below the specified 1e-12 tolerance.
- Both saved figures are readable, show all seventeen countries, mark the
  cross-regime scope, and distinguish own-profile distance from peer-distance
  change. No line bridges the measurement break.

## Findings

Mean base-2 Jensen–Shannon distance falls from **0.08326013374402202** in August
to **0.0627982886486717** in May: change **-0.02046184509535033**, or
**-24.575801377234%** (24.58% lower when rounded). This compares the same
17 countries and 136 unordered pairs. May remains below August despite the
separate April–May increase; this does not imply a monotonic behavioral path.

Sixteen countries have lower mean peer distance; Indonesia alone has higher
distance (+0.013921). Brazil has the largest decline (-0.078017) and largest
own-profile distance (0.202691); Japan's decline is -0.041126. Ninety-nine pairs
become closer and thirty-seven farther. These are dependent descriptive counts.

Automation-country rank correlation is **0.791667** (17 observations);
pair-distance rank correlation is **0.680473** (136 observations). These are
different rankings and have no p-values or uncertainty intervals. Conditional
automation mean changes from **50.90% to 47.91%**, population SD from **5.43 to
2.44 pp**; the original-denominator mean changes from **49.65% to 46.72%**,
SD from **5.40 to 2.36 pp**.

Every single-country exclusion preserves the decline, with changes between
**-0.025046** (exclude Indonesia) and **-0.012788** (exclude Brazil).
Every four-mode reconditioned comparison is available and negative: directive
omitted -0.017281; feedback loop -0.017001; learning -0.012291; task iteration
-0.022380; validation -0.022397. These are new endpoint sensitivities, not
results inherited from the earlier contrasts. They assess arithmetic dependence
without establishing measurement equivalence or causal attribution.

Across the published profiles, every country has less directive use and more
feedback loops and task iteration in May. Learning falls in sixteen countries;
India is the exception. These common changes can coexist with residual
differentiation and reflect source/product changes as well as possible behavior.
Country examples and patterns are exploratory illustrations after full exposure.

## Interpretation and delivery

August covers Free/Pro and approximately one week; May covers chat/Cowork across
Free/Pro/Max and a calendar month. Stable labels do not establish stable
classifier calibration. Fixed countries do not fix users or conversations,
and normalization does not remove these differences. Country/period intercepts
cannot separate measurement change from behavior. The result supports lower
dispersion of **published profiles**, without attributing the full decline to
convergence in underlying practices or identifying institutional isomorphism.

Integrate reviewed saved outputs into
`results/research_note/g20_profiles_v1/20261016T071919171212Z_editorial_v2/`.
Preserve the prior note, all released bundles, and the complete Stage 11 run.
The new edition includes the eleven CSV/parquet tables, four figures,
execution/provenance snapshots, this review and its hash-pinned decision.
The edition manifest describes the analytical addition; historical release and
editorial manifests continue to describe their earlier versions.
