"""Tests for the ingestion utilities."""

from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import numpy as np
import pandas as pd

SRC_PATH = Path(__file__).resolve().parents[1] / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from data import (  # noqa: E402
    CatalogRow,
    ingest_light_curves,
    load_catalog,
    load_light_curve_csv,
)


def _write_csv(path: Path, content: str) -> None:
    path.write_text(textwrap.dedent(content).strip() + "\n", encoding="utf-8")


def test_load_catalog_filters_and_labels(tmp_path: Path) -> None:
    catalog_path = tmp_path / "catalog.csv"
    _write_csv(
        catalog_path,
        """
        # generated for testing
        target_id,Disposition,extra
        1234,PC,sector-01
        2345,FP,sector-02
        3456,,sector-03
        ,PC,sector-04
        4567,KP,sector-05
        """,
    )

    records = load_catalog(
        catalog_path,
        survey="tess",
        target_column="target_id",
        disposition_column="Disposition",
        label_map={"pc": 1, "fp": 0},
    )

    assert len(records) == 2
    first = records[0]
    assert first.target_id == "1234"
    assert first.label == 1
    assert first.extra["extra"] == "sector-01"


def test_load_light_curve_csv_detects_columns(tmp_path: Path) -> None:
    curve_path = tmp_path / "lc.csv"
    _write_csv(
        curve_path,
        """
        # comment header
        TIME,PDCSAP_FLUX,QUALITY
        0.0,1.0,0
        0.1,0.999,None
        0.2,invalid,0
        0.3,,0
        0.4,0.998,0
        """,
    )

    curve = load_light_curve_csv(curve_path)
    assert curve.sample_count == 3  # only numeric, non-null samples remain
    assert np.isclose(curve.time[0], 0.0)
    assert np.isclose(curve.flux[-1], 0.998)


def test_ingest_light_curves_with_template(tmp_path: Path) -> None:
    # Prepare catalog entries manually to avoid relying on large real datasets.
    catalog = [
        CatalogRow(
            target_id="TOI-123",
            label=1,
            disposition="PC",
            survey="tess",
            source_path=tmp_path / "catalog.csv",
            extra={},
        ),
        CatalogRow(
            target_id="TOI-999",
            label=0,
            disposition="FP",
            survey="tess",
            source_path=tmp_path / "catalog.csv",
            extra={},
        ),
    ]

    curves_dir = tmp_path / "curves"
    curves_dir.mkdir()

    rng = np.random.default_rng(42)
    frames = [
        pd.DataFrame(
            {"time": np.linspace(0, 1, 250), "flux": rng.normal(0.0, 0.0005, 250)}
        ),
        pd.DataFrame(
            {"time": np.linspace(0, 1, 50), "flux": rng.normal(0.0, 0.0005, 50)}
        ),
    ]
    frames[0].to_csv(curves_dir / "TOI-123.csv", index=False)
    frames[1].to_csv(curves_dir / "TOI-999.csv", index=False)

    ingested = ingest_light_curves(
        catalog,
        curve_dir=curves_dir,
        filename_template="{target_id}.csv",
        min_samples=100,
    )

    assert len(ingested) == 1
    sample = ingested[0]
    assert sample.target_id == "TOI-123"
    assert sample.curve.sample_count == 250
