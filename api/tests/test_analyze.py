"""Tests for the /analyze endpoint."""

from __future__ import annotations

import csv
import io

import numpy as np
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _make_light_curve_csv(*, has_transit: bool) -> bytes:
    generator = np.random.default_rng(12 if has_transit else 21)
    time = np.linspace(0.0, 12.0, 1200)
    flux = np.ones_like(time)
    flux += generator.normal(0.0, 4e-4, size=time.size)

    if has_transit:
        period = 2.5
        duration = 0.12
        depth = 0.0025
        phase = 0.3
        indices = np.mod(time - phase, period) < duration
        flux[indices] -= depth

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["time", "flux"])
    writer.writerows(zip(time, flux, strict=False))
    return buffer.getvalue().encode("utf-8")


def test_analyze_endpoint_returns_prediction() -> None:
    csv_bytes = _make_light_curve_csv(has_transit=True)
    response = client.post(
        "/analyze/",
        files={"file": ("sample.csv", csv_bytes, "text/csv")},
    )

    assert response.status_code == 200
    payload = response.json()

    assert "analysis_id" in payload
    assert "result" in payload
    assert "metrics" in payload
    assert "plots" in payload

    result = payload["result"]
    assert isinstance(result["confidence"], float)
    assert 0.0 <= result["confidence"] <= 100.0
    assert isinstance(result["reasons"], list)
    assert result["reasons"]

    metrics = payload["metrics"]
    assert "data_points" in metrics
    assert metrics["data_points"] == 1200
    assert "model_version" in metrics
    assert "feature_vector" in metrics

    plots = payload["plots"]
    assert "light_curve" in plots
    assert plots["light_curve"].startswith("data:image/png;base64,")


def test_analyze_endpoint_rejects_invalid_extension() -> None:
    response = client.post(
        "/analyze/",
        files={"file": ("sample.txtx", b"", "text/plain")},
    )
    assert response.status_code == 400
