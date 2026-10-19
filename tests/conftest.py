"""Synthetic publisher schemas shared by the active pipeline checks.

The source generator is preserved from the inspection-workflow fixture;
it does not load archived code, review decisions or empirical observations.
"""

from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def project(tmp_path: Path) -> Path:
    """Build a tiny project with real schemas and no published observations."""
    (tmp_path / "docs").mkdir()

    sources = [
        (
            "release_2025_09_15",
            "data/intermediate/"
            "aei_raw_claude_ai_2025-08-04_to_2025-08-11.csv",
            "legacy",
            [("2025-08-04", "2025-08-11")],
        ),
        (
            "release_2026_01_15",
            "data/intermediate/"
            "aei_raw_claude_ai_2025-11-13_to_2025-11-20.csv",
            "legacy",
            [("2025-11-13", "2025-11-20")],
        ),
        (
            "release_2026_03_24",
            "data/aei_raw_claude_ai_2026-02-05_to_2026-02-12.csv",
            "legacy",
            [("2026-02-05", "2026-02-12")],
        ),
        (
            "release_2026_06_26",
            "data/aei_claude_ai_2026-06-26.csv",
            "monthly",
            [("2026-04-01", "2026-05-01"), ("2026-05-01", "2026-06-01")],
        ),
    ]
    for release, filename, schema, windows in sources:
        path = tmp_path / "data/raw" / release / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        (tmp_path / "data/raw" / release / "data_documentation.md").write_text(
            "Synthetic source documentation.\n", encoding="utf-8"
        )
        rows = []
        for start, end in windows:
            country_ids = (
                ["NA", "US"] if schema == "legacy" else ["NAM", "USA"]
            )
            for geography, geo_id in [
                ("country", country_ids[0]),
                ("country", country_ids[1]),
                ("global", "GLOBAL"),
            ]:
                values = [
                    ("directive", "20"),
                    ("feedback_loop", "20"),
                    ("learning", "20"),
                    ("task_iteration", "20"),
                    ("validation", "0"),
                    ("none", "20"),
                ]
                if schema == "monthly":
                    values += [
                        ("bucket_automation", "50"),
                        ("bucket_augmentation", "50"),
                    ]
                for measure, value in values:
                    row = {
                        "date_start": start,
                        "date_end": end,
                        "geo_id": geo_id,
                        "value": value,
                    }
                    if schema == "legacy":
                        row.update(
                            {
                                "geography": geography,
                                "facet": "collaboration",
                                "level": "0",
                                "variable": "collaboration_pct",
                                "cluster_name": {
                                    "feedback_loop": "feedback loop",
                                    "task_iteration": "task iteration",
                                }.get(measure, measure),
                                "platform_and_product": "Synthetic Claude",
                            }
                        )
                    else:
                        row.update(
                            {
                                "geo_level": geography,
                                "category_name": "overall",
                                "hierarchy_level": "0",
                                "metric_id": f"collaboration_{measure}_pct",
                                "node_name": "Overall",
                            }
                        )
                    rows.append(row)
        if schema == "legacy" and release == "release_2025_09_15":
            rows.append(
                {
                    **rows[0],
                    "facet": "onet_task::collaboration",
                    "variable": "onet_task_collaboration_pct",
                }
            )
        if schema == "monthly":
            rows.extend(
                [
                    {**rows[0], "category_name": "onet"},
                    {**rows[0], "geo_level": "subregion"},
                    {**rows[0], "metric_id": "usage_pct"},
                ]
            )
        pd.DataFrame(rows).to_csv(path, index=False)
    return tmp_path
