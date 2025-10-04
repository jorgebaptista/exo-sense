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
    ├── notebooks/     # Jupyter notebooks (Colab development)
    │   ├── exploration/   # Data exploration
    │   ├── development/   # Algorithm development  
    │   └── examples/      # Usage examples
    ├── data/          # Load TESS/Kepler data
    ├── detection/     # BLS transit search
    ├── vetting/       # Odd/even + secondary checks
    └── visualization/ # Generate plots
```

## Tech Stack

- **Frontend**: Next.js 14, TypeScript, Tailwind, Plotly
- **Backend**: FastAPI, Pydantic v2, Uvicorn  
- **ML**: NumPy, Astropy, Lightkurve, Wōtan, BLS
- **Development**: Google Colab (clone repo → develop → commit back)
- **Quality**: MyPy, Ruff, Pytest, Jest

## Data Flow

```text
TIC/KIC Input → API → ML Pipeline → Plots + Metrics → Frontend → PDF Export
```

## Google Colab Workflow

**For ML Development**: Google Colab while staying synced with the repo:

1. **Clone in Colab**: `!git clone https://github.com/jorgebaptista/exo-sense.git`
2. **Navigate to ML**: `%cd exo-sense/ml`
3. **Develop in notebooks/**: Create/edit notebooks in the `notebooks/` folder
4. **Extract production code**: Move proven algorithms from notebooks to the production folders (`data/`, `detection/`, `vetting/`, etc.)
5. **Commit & push**: `!git add . && git commit -m "Added BLS detection" && git push`

This keeps experimental notebook development separate from production ML code, but all within the same `ml/` package structure. The API imports from the production folders, not the notebooks.

## Key Principles

1. **Separation**: Frontend (UI) ↔ API (logic) ↔ ML (science)
2. **Modularity**: Independent development and testing
3. **Colab-friendly**: Clone repo in Colab → develop notebooks → extract to `ml/`
4. **Standards**: Follow AGENTS.md guidelines strictly
