# ExoSense

> Making sense of distant worlds through open NASA data and AI.

**ExoSense** is a web platform that analyzes stellar light curves from NASA missions (TESS/Kepler) to detect and vet exoplanet candidates. Built for rapid exploration with transparent astrophysical checks and instant demo examples.

## What It Does

1. **Load** a light curve (NASA TIC/KIC ID or upload CSV/FITS)
2. **Analyze** with fast transit detection (BLS algorithm + detrending)
3. **Vet** candidates using odd/even depth checks, secondary eclipse detection, and signal metrics
4. **Export** a 1-page PDF report with plots, metrics, and interpretable reasons

**Demo Mode** provides 4 cached examples (confirmed planet, eclipsing binary, variable star, systematics) for instant offline results.

## Architecture

- **Frontend**: Next.js (PWA) on Vercel
- **API**: FastAPI on Cloud Run
- **Science**: BLS/TLS transit search, Wōtan detrending, rule-based vetting (optional ML)
- **Data**: Lightkurve (MAST) + NASA Exoplanet Archive

## Project Status

🚧 **Early development** — built for a 48-hour hackathon demo. Core MVP in progress
