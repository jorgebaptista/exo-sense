"""Utilities for ingesting labeled light-curve datasets."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from detection.types import LightCurve

logger = logging.getLogger(__name__)

DEFAULT_TIME_COLUMNS = ("time", "TIME", "bjd", "BJD", "bjd_tdb", "BKJD", "btjd", "BTJD")
DEFAULT_FLUX_COLUMNS = (
    "flux",
    "FLUX",
    "pdcsap_flux",
    "PDCSAP_FLUX",
    "sap_flux",
    "SAP_FLUX",
    "flux_norm",
    "normalized_flux",
)


@dataclass(frozen=True)
class CatalogRow:
    """Metadata record parsed from a catalog CSV file."""

    target_id: str
    label: int
    disposition: str
    survey: str
    source_path: Path
    extra: dict[str, object]


@dataclass(frozen=True)
class LabeledLightCurve:
    """A light curve paired with its binary label and metadata."""

    curve: LightCurve
    label: int
    target_id: str
    source_path: Path
    disposition: str
    survey: str
    extra: dict[str, object]

    def as_tuple(self) -> tuple[LightCurve, int]:
        """Return (curve, label) pair for compatibility with training code."""

        return self.curve, self.label


def load_catalog(
    path: Path,
    *,
    survey: str,
    target_column: str,
    disposition_column: str,
    label_map: Mapping[str, int],
    comment: str = "#",
) -> list[CatalogRow]:
    """Load a catalog exported from the NASA Exoplanet Archive.

    The file typically starts with comment rows (#) that describe the
    columns, which `pandas.read_csv` can skip via the ``comment`` parameter.

    Args:
        path: CSV file with metadata records.
        survey: Name of the survey (e.g. ``"kepler"``, ``"tess"``).
        target_column: Column containing the target identifier.
        disposition_column: Column describing the disposition (used for labels).
        label_map: Case-insensitive mapping from disposition values to labels
            (0 or 1). Values not present in the mapping are ignored.
        comment: Character used to mark header comments (defaults to ``"#"``).

    Returns:
        A list of :class:`CatalogRow` with normalized metadata.
    """

    if not path.exists():
        raise FileNotFoundError(path)

    df = pd.read_csv(path, comment=comment)

    if target_column not in df.columns or disposition_column not in df.columns:
        missing = {target_column, disposition_column} - set(df.columns)
        raise KeyError(f"Missing required columns in {path.name}: {missing}")

    records: list[CatalogRow] = []
    normalized_map = {key.lower(): label for key, label in label_map.items()}

    for _, row in df.iterrows():
        disposition_raw = str(row[disposition_column]).strip()
        if not disposition_raw:
            continue
        disposition_norm = disposition_raw.lower()
        if disposition_norm not in normalized_map:
            continue

        label = normalized_map[disposition_norm]

        raw_target = row[target_column]
        if pd.isna(raw_target):
            continue

        if isinstance(raw_target, float) and float(raw_target).is_integer():
            target = str(int(raw_target))
        else:
            target = str(raw_target).strip()

        if not target or target.lower() == "nan":
            continue

        extra_metadata = {
            column: row[column]
            for column in df.columns
            if column not in {target_column, disposition_column}
        }

        records.append(
            CatalogRow(
                target_id=target,
                label=int(label),
                disposition=disposition_raw,
                survey=survey,
                source_path=path,
                extra=extra_metadata,
            )
        )

    logger.info("Loaded %d labeled entries from %s", len(records), path)
    return records


def _find_column(columns: Sequence[str], candidates: Sequence[str]) -> str | None:
    lowered = {column.lower(): column for column in columns}
    for candidate in candidates:
        lowered_candidate = candidate.lower()
        if lowered_candidate in lowered:
            return lowered[lowered_candidate]
    return None


def load_light_curve_csv(
    path: Path,
    *,
    time_columns: Sequence[str] = DEFAULT_TIME_COLUMNS,
    flux_columns: Sequence[str] = DEFAULT_FLUX_COLUMNS,
    comment: str = "#",
) -> LightCurve:
    """Load a light curve CSV file and return a :class:`LightCurve` instance."""

    if not path.exists():
        raise FileNotFoundError(path)

    df = pd.read_csv(path, comment=comment)
    if df.empty:
        raise ValueError(f"Light curve file {path} contains no rows")

    columns = list(df.columns)
    time_column = _find_column(columns, time_columns)
    flux_column = _find_column(columns, flux_columns)
    if time_column is None or flux_column is None:
        raise KeyError(
            f"Could not identify time/flux columns in {path.name}; columns available: {list(df.columns)}"
        )

    time_series = pd.to_numeric(df[time_column], errors="coerce")
    flux_series = pd.to_numeric(df[flux_column], errors="coerce")
    mask = time_series.notna() & flux_series.notna()
    if not mask.any():
        raise ValueError(f"No numeric samples remaining after cleaning {path}")

    time_values = time_series[mask].to_numpy(dtype=np.float64, copy=False)
    flux_values = flux_series[mask].to_numpy(dtype=np.float64, copy=False)
    curve = LightCurve.from_sequences(time_values, flux_values)
    return curve.clip_non_finite().ensure_sorted()


def ingest_light_curves(
    catalog: Iterable[CatalogRow],
    *,
    curve_dir: Path,
    filename_column: str | None = None,
    filename_template: str | None = None,
    time_columns: Sequence[str] = DEFAULT_TIME_COLUMNS,
    flux_columns: Sequence[str] = DEFAULT_FLUX_COLUMNS,
    min_samples: int = 200,
) -> list[LabeledLightCurve]:
    """Create labeled light-curve objects using catalog metadata.

    Args:
        catalog: Iterable of :class:`CatalogRow`.
        curve_dir: Directory that contains the curve CSV files.
        filename_column: Optional name of a column in ``CatalogRow.extra`` that stores
            the filename for the associated light curve.
        filename_template: Template string (e.g. ``"{target_id}.csv"``) used when a
            filename column is not provided. Either ``filename_column`` or the
            template must be supplied.
        time_columns: Candidate column names for time data.
        flux_columns: Candidate column names for flux data.
        min_samples: Minimum number of samples required to keep a light curve.

    Returns:
        A list of :class:`LabeledLightCurve` ready for feature extraction.
    """

    if filename_column is None and filename_template is None:
        raise ValueError("Either filename_column or filename_template must be provided")

    ingested: list[LabeledLightCurve] = []
    curve_dir = curve_dir.expanduser().resolve()
    if not curve_dir.exists():
        raise FileNotFoundError(curve_dir)

    for entry in catalog:
        relative_path: Path | None = None

        if filename_column is not None:
            filename_value = entry.extra.get(filename_column)
            if not filename_value or not isinstance(filename_value, str):
                logger.debug(
                    "Skipping %s: missing filename column %s",
                    entry.target_id,
                    filename_column,
                )
                continue
            relative_path = Path(filename_value)
        elif filename_template is not None:
            try:
                relative_path = Path(
                    filename_template.format(target_id=entry.target_id)
                )
            except KeyError as exc:  # pragma: no cover - format errors are unexpected
                logger.warning(
                    "Filename template missing key for %s: %s", entry.target_id, exc
                )
                continue

        if relative_path is None:
            logger.debug(
                "Skipping %s: no filename information available", entry.target_id
            )
            continue

        curve_path = (curve_dir / relative_path).resolve()
        if not curve_path.exists():
            logger.debug(
                "Skipping %s: curve file not found at %s", entry.target_id, curve_path
            )
            continue

        try:
            curve = load_light_curve_csv(
                curve_path,
                time_columns=time_columns,
                flux_columns=flux_columns,
            )
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning(
                "Failed to load %s (%s): %s", entry.target_id, curve_path.name, exc
            )
            continue

        if curve.sample_count < min_samples:
            logger.debug(
                "Skipping %s: only %d samples", entry.target_id, curve.sample_count
            )
            continue

        ingested.append(
            LabeledLightCurve(
                curve=curve,
                label=entry.label,
                target_id=entry.target_id,
                source_path=curve_path,
                disposition=entry.disposition,
                survey=entry.survey,
                extra=entry.extra,
            )
        )

    logger.info("Ingested %d light curves from %s", len(ingested), curve_dir)
    return ingested


__all__ = [
    "CatalogRow",
    "LabeledLightCurve",
    "load_catalog",
    "load_light_curve_csv",
    "ingest_light_curves",
]
