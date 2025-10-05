"""Data loading and preprocessing for TESS and Kepler light curves."""

from .ingestion import (
    CatalogRow,
    LabeledLightCurve,
    ingest_light_curves,
    load_catalog,
    load_light_curve_csv,
)

__all__ = [
    "CatalogRow",
    "LabeledLightCurve",
    "ingest_light_curves",
    "load_catalog",
    "load_light_curve_csv",
]
