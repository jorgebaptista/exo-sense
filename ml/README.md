# ExoSense ML Package

Python package for exoplanet detection and vetting using NASA light curves.

## Development

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run type checking
mypy . --strict

# Run linting
ruff check .
ruff format --check .

# Run tests
pytest tests/ -v --cov=ml
```

## Modules

- `ingest.py` - Load light curves from TESS/Kepler
- `detect.py` - BLS/TLS transit search
- `checks.py` - Odd/even, secondary eclipse vetting
- `features.py` - Feature extraction
- `vetter_rules.py` - Rule-based classification
