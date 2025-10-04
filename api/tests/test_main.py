"""Tests for main API endpoints."""

from __future__ import annotations

import io
from pathlib import Path

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _sample_light_curve_csv() -> bytes:
    """Create a synthetic light curve with two deep transits."""

    lines = ["time,flux"]
    for idx in range(20):
        flux = 1.0
        if idx in {5, 15}:
            flux = 0.2
        lines.append(f"{idx},{flux}")
    return "\n".join(lines).encode("utf-8")


def test_health_check() -> None:
    """Test health check endpoint."""

    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_root_endpoint() -> None:
    """Test root endpoint."""

    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "ExoSense API" in data["message"]


def test_analyze_returns_sonification_payload() -> None:
    """Analyze endpoint should emit sonification metadata and persist it."""

    csv_bytes = _sample_light_curve_csv()
    files = {"file": ("sample.csv", io.BytesIO(csv_bytes), "text/csv")}

    response = client.post("/analyze/", files=files)
    assert response.status_code == 200

    payload = response.json()
    assert "analysis_id" in payload
    assert payload["sonification"] is not None

    sonification = payload["sonification"]
    assert len(sonification["time"]) == 20
    assert any(sonification["in_transit"])

    analysis_id = payload["analysis_id"]
    stored_path = Path("storage/sonify") / f"{analysis_id}.json"
    assert stored_path.exists()


def test_sonify_endpoint_streams_audio() -> None:
    """Sonify endpoint should stream rendered audio for an analysis."""

    csv_bytes = _sample_light_curve_csv()
    files = {"file": ("sample.csv", io.BytesIO(csv_bytes), "text/csv")}
    analysis_response = client.post("/analyze/", files=files)
    analysis_id = analysis_response.json()["analysis_id"]

    url = (
        f"/sonify/?analysis_id={analysis_id}&mode=flux_pitch&quantize=true&stereo=true"
    )
    audio_response = client.get(url)

    assert audio_response.status_code == 200
    assert audio_response.headers["content-type"].startswith("audio/wav")
    assert int(audio_response.headers["X-Audio-Sample-Rate"]) == 16_000
    assert len(audio_response.content) > 500
