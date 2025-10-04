# ExoSense Architecture

## Overview

Web platform for exoplanet detection using NASA light curves: **Upload → Analyze → Export**

## Structure

```text
exo-sense/
├── frontend/          # Next.js + TypeScript
│   ├── app/           # Pages (analyze, demo, results)
│   ├── components/    # UI, forms, plots, results
│   └── lib/           # API client, types, utils
│
├── api/               # FastAPI backend
│   ├── routers/       # Endpoints (analyze, upload, report)
│   ├── services/      # Business logic
│   └── models/        # Request/response schemas
│
└── ml/                # Python science package  
    ├── src/           # Source code (installable package)
    │   ├── __init__.py    # Package initialization
    │   ├── utils.py       # Common utilities
    │   ├── data/          # Load TESS/Kepler data
    │   ├── detection/     # BLS transit search
    │   ├── vetting/       # Odd/even + secondary checks
    │   └── visualization/ # Generate plots
    ├── tests/         # Unit tests
    ├── notebooks/     # Jupyter notebooks (Colab development)
    │   ├── exploration/   # Data exploration
    │   ├── development/   # Algorithm development  
    │   └── examples/      # Usage examples
    └── pyproject.toml # Modern Python packaging
```

## Tech Stack

- **Frontend**: Next.js 14, TypeScript, Tailwind, Plotly
- **Backend**: FastAPI, Pydantic v2, Uvicorn  
- **ML**: NumPy, Astropy, Lightkurve, Matplotlib
- **Deployment**: Railway (backend), Vercel (frontend)
- **Quality**: MyPy, Ruff, Pytest, Jest

## Data Flow

```text
TIC/KIC Input → API → ML Pipeline → Plots + Metrics → Frontend → PDF Export
```

## Deployment

### Railway (Backend API)

- Automatic deployment from `main` branch
- Environment: `api/` folder
- Start command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Python 3.11+ with scientific dependencies

### Vercel (Frontend)

- Automatic deployment from `main` branch  
- Environment: `frontend/` folder
- Build: `npm run build`
- Next.js optimized production build

## Google Colab Workflow

**For ML Development**: Google Colab while staying synced with the repo:

1. **Clone in Colab**: `!git clone https://github.com/jorgebaptista/exo-sense.git`
2. **Navigate to ML**: `%cd exo-sense/ml`
3. **Install package**: `!pip install -e .` (installs the `src/` code)
4. **Develop in notebooks/**: Create/edit notebooks in the `notebooks/` folder
5. **Use clean imports**: `from utils import compute_rms`, `from detection import bls_search`
6. **Extract production code**: Move proven algorithms from notebooks to the `src/` folders
7. **Commit & push**: `!git add . && git commit -m "Added BLS detection" && git push`

This keeps experimental notebook development separate from production ML code in `src/`, but allows clean imports throughout. The API imports from the installed package modules.

## Key Principles

1. **Separation**: Frontend (UI) ↔ API (logic) ↔ ML (science)
2. **Modularity**: Independent development and testing
3. **Clean imports**: `from utils import compute_rms` (no nested packages)
4. **Colab-friendly**: Clone repo → install package → develop notebooks → extract to `src/`
5. **Standards**: Follow AGENTS.md guidelines strictly
