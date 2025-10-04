# ExoSense Development Guide

> **Context**: See [README.md](./README.md) for project overview and [docs/architecture.md](./docs/architecture.md) for detailed structure.
> **Goal**: Web platform for exoplanet detection using NASA light curves  
> **Stack**: Next.js + FastAPI + Python ML  
> **Deployment**: Railway (API) + Vercel (Frontend)
> **🚨 CRITICAL**: Every session MUST end with 100% clean checks (MyPy, Ruff, ESLint, tests) across ALL folders. No exceptions.
> **Always run MyPy, Ruff, ESLint and all tests in `frontend`, `api`, and `ml` before ending your session.**

## Code Standards

1. **Reuse > Reinvent**: Search existing code first
2. **Zero Redundancy**: Extract repeated patterns into shared components/helpers immediately
3. **Tests Required**: Unit tests for business logic, integration tests for API
4. **Type Safety**: TypeScript strict + MyPy strict
5. **Quality Gates**: All (whole repo) linting/tests must pass before finishing
6. **NO GIT**: Never commit - user handles git operations

## Quality Checks (Required before finishing)

```bash
# Documentation
markdownlint "**/*.md" --ignore "**/node_modules/**" --ignore "**/.next/**"

# Frontend
cd frontend && npm run type-check && npm run lint && npm test

# Backend  
cd api && mypy . && ruff check . && ruff format --check . && pytest tests/ -v

# ML
cd ml && mypy . --explicit-package-bases && ruff check . && pytest tests/ -v

# Type stub check (if mypy fails with missing stubs)
cd api && python -m pip install -r requirements-dev.txt
```

## API Endpoints

- `GET /healthz` → Health check
- `POST /analyze/` → File upload + exoplanet detection  
- `POST /report/generate` → PDF generation

## Deployment

- **Railway**: Automatic API deployment (`api/` folder)
- **Vercel**: Automatic frontend deployment (`frontend/` folder)
- **Config**: `Procfile`, `railway.json`, `runtime.txt` in `api/`
