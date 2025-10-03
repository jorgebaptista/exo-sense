# ExoSense API

FastAPI backend for exoplanet detection and analysis.

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
pytest tests/ -v --cov=.
```

## API Endpoints

- `GET /healthz` - Health check
- `POST /analyze` - Analyze light curve
- `POST /report` - Generate PDF report

See [AGENTS.md](../AGENTS.md) for full API contract.
