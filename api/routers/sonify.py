"""Endpoints for serving sonified light-curve audio."""

from __future__ import annotations

import io
import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from services.sonification import SAMPLE_RATE, SonifyMode, generate_wav_bytes

router = APIRouter(prefix="/sonify", tags=["sonify"])

DATA_DIR = Path("storage/sonify")
AUDIO_DIR = DATA_DIR / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)


@router.get("/")
async def sonify_analysis(
    analysis_id: str,
    mode: SonifyMode = SonifyMode.TRANSIT_PING,
    speed: float = Query(1.0, gt=0.1, lt=5.0),
    quantize: bool = Query(False),
    stereo: bool = Query(False),
) -> StreamingResponse:
    """Render sonification audio for a stored analysis."""

    json_path = DATA_DIR / f"{analysis_id}.json"
    if not json_path.exists():
        raise HTTPException(status_code=404, detail="Sonification data not found")

    try:
        with open(json_path, encoding="utf-8") as src:
            series = json.load(src)
    except json.JSONDecodeError as exc:  # pragma: no cover
        raise HTTPException(
            status_code=500, detail="Corrupted sonification data"
        ) from exc

    audio_bytes = generate_wav_bytes(series, mode, speed, quantize, stereo)

    filename = f"{analysis_id}_{mode.value}.wav"
    audio_path = AUDIO_DIR / filename
    with open(audio_path, "wb") as audio_file:
        audio_file.write(audio_bytes)

    headers = {
        "Content-Disposition": f'attachment; filename="{filename}"',
        "X-Audio-Sample-Rate": str(SAMPLE_RATE),
    }
    return StreamingResponse(
        io.BytesIO(audio_bytes), media_type="audio/wav", headers=headers
    )
