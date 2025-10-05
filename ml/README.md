# ExoSense ML Package

Machine learning utilities for detecting transiting exoplanets from stellar light curves. The package provides:

- Robust feature extraction for 1D photometric time series.
- A hybrid training pipeline that mixes curated Kepler light curves with synthetic augmentation to build a scikit-learn random forest classifier.
- A lightweight inference wrapper that can be embedded in the API.

## Development

```bash
# Create and activate virtual environment (recommended)
python3.11 -m venv .venv
source .venv/bin/activate

# Install runtime and development dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Static analysis
mypy src
ruff check .

# Run unit tests
pytest -v --cov=src
```

## Key modules

- `src/detection/types.py` — Typed helpers for representing and validating light curves.
- `src/detection/features.py` — Feature engineering and statistics used by the classifier.
- `src/detection/training.py` — Real/synthetic dataset builder and model training utility.
- `src/detection/model.py` — High-level wrapper for loading, persisting, and scoring the classifier.
- `src/detection/simulation.py` — Random light-curve simulator used for training and tests.
- `src/data/ingestion.py` — Catalog + light-curve ingestion utilities for building labeled datasets from NASA exports or local manifests.

### Ingestion pipeline

Real survey data is now bundled in `src/data/`:

- `kepler_curated_catalog.csv` describes a small, hand-picked subset of Kepler targets with their dispositions and relative CSV filenames.
- `light_curves/` stores the corresponding PDCSAP-flux light curves exported through the ingestion utilities.

The helper functions in `src/data/ingestion.py` provide:

- `load_catalog(...)` to normalise disposition labels coming from TOI/KOI tables (comment-prefixed rows are handled automatically).
- `load_light_curve_csv(...)` to auto-detect common time/flux column names (e.g. `TIME`, `PDCSAP_FLUX`).
- `ingest_light_curves(...)` to combine catalogs with a directory of light-curve files, yielding labeled samples ready for feature extraction.

`train_default_model()` relies on `build_training_dataset()` to ingest this curated catalog and then augment it with simulator output for class balance. Remove or replace the files in `src/data/light_curves/` to point the pipeline at a different dataset; any missing files automatically trigger a synthetic-only fallback.

## Artifacts

Serialized models are written to `ml/artifacts/` as `exoplanet_classifier.joblib`. The artifact is created automatically when inference runs for the first time, or you can force regeneration by deleting the file and invoking `train_default_model()` manually.
