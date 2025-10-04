# AGENTS.md — Development Guidelines

> **Context**: See [README.md](./README.md) for project overview and [docs/architecture.md](./docs/architecture.md) for detailed structure.

This document provides essential guidelines for AI coding agents and contributors working on ExoSense.

## Project Overview

**Goal**: Web platform for exoplanet detection using NASA light curves (TESS/Kepler) optimized for 48-hour hackathon demo.

**Stack**: Next.js frontend + FastAPI backend + Python ML pipeline

**Core Flow**: Load light curve → BLS transit search → Vet with odd/even + secondary checks → Export PDF

## Non-Negotiable Code Standards

1. **Reuse > Reinvent**: Always search workspace for existing code before creating new
2. **Zero Redundancy**: Extract repeated patterns into shared components/helpers immediately  
3. **Type Safety**: TypeScript strict mode (frontend), mypy strict (backend)
4. **Tests Required**: Unit tests for business logic, integration tests for API
5. **All Tests Pass**: Run type-check, lint, test before finishing any session
6. **NO GIT OPERATIONS**: Never commit, add, or push with git - user handles all git operations

## Architecture

### Frontend (`frontend/`)

- **Tech**: Next.js 14+, TypeScript, Tailwind
- **Key Files**: `app/page.tsx` (home), `components/ui/` (reusable), `lib/api.ts` (API client)

### Backend (`api/`)

- **Tech**: FastAPI, Pydantic v2
- **Structure**: `main.py` (routes), `models/` (request/response), `services/` (business logic)

### ML Pipeline (`ml/` + `notebooks/`)

- **Tech**: Python 3.11+, NumPy, Lightkurve, Astropy
- **Development**: Google Colab (clone repo → develop in `notebooks/` → extract to `ml/`)
- **Key Modules**: `ingest.py`, `detect.py` (BLS), `checks.py` (odd/even, secondary)

## Session Workflow

### Before Starting

1. `git pull origin main`
2. Search codebase for similar functionality
3. Check README for context

### Before Finishing

**Must run these checks**:

```bash
# Frontend
cd frontend && npm run type-check && npm run lint && npm run test

# Backend  
cd api && mypy . --strict && ruff check . && pytest tests/

# ML
cd ml && mypy . --strict && ruff check . && pytest tests/
```

**All must pass green** before committing.

## API Contract (MVP)

- `GET /healthz` → `{ "status": "ok" }`
- `POST /analyze` → Takes TIC/KIC ID or file upload, returns metrics + plots + label
- `POST /report` → PDF generation

## Demo Requirements

✅ **Demo Mode** (4 cached examples) works offline  
✅ **Live mode** works on ≥1 real TIC/KIC  
✅ **Interpretability** with clear reason codes  
✅ **One-click PDF** export  

That's it. Keep it simple, follow the standards, make it work. 🚀
