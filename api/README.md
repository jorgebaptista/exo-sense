# ExoSense API

FastAPI backend for exoplanet detection and analysis.

## Overview

The `/analyze` endpoint now streams uploaded light curves through the shared `ml` package:

1. Light curves are parsed and validated.
2. The trained `ExoplanetModel` generates a probability-based classification and feature vector.
3. Diagnostic plots and metadata are returned to the client.

The first call to the model will lazily train a scikit-learn classifier (or load an existing artifact from `ml/artifacts/exoplanet_classifier.joblib`).

## Development

```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Start development server (like npm run dev for Next.js)
uvicorn main:app --reload --port 8000

# Run type checking
mypy . --strict

# Run linting
ruff check .
ruff format --check .

# Run tests
pytest tests/ -v --cov=.
```

## API Endpoints

- `GET /healthz` - Health check
- `POST /analyze` - Analyze a light curve with the ML classifier
- `POST /report` - Generate PDF report

See [AGENTS.md](../AGENTS.md) for full API contract.
