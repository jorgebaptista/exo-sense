"""Audio rendering utilities for light-curve sonification."""

from __future__ import annotations

import io
import math
import wave
from enum import Enum
from typing import Any

import numpy as np

SAMPLE_RATE = 16_000
_BASE_DURATION = 0.02
_MIN_DURATION = 0.005
_PENTATONIC_STEPS = (0, 2, 4, 7, 9)


class SonifyMode(str, Enum):
    """Supported sonification render modes."""

    TRANSIT_PING = "transit_ping"
    FLUX_PITCH = "flux_pitch"
    ODD_EVEN = "odd_even"


def clamp(value: float, minimum: float, maximum: float) -> float:
    """Clamp a value between bounds."""

    return max(minimum, min(maximum, value))


def _quantize_frequency(freq: float) -> float:
    """Snap a frequency to a pleasant pentatonic scale."""

    if freq <= 0:
        return 220.0

    midi = 69 + 12 * math.log2(freq / 440.0)
    octave = math.floor(midi / 12)
    pitch_in_octave = midi - octave * 12
    nearest_step = min(
        _PENTATONIC_STEPS,
        key=lambda step: abs(step - pitch_in_octave),
    )
    quantized_midi = octave * 12 + nearest_step
    return 440.0 * (2 ** ((quantized_midi - 69) / 12))


def _prepare_boolean_array(values: Any, size: int) -> np.ndarray:
    """Normalize boolean list-like inputs to a numpy array of target size."""

    array = np.asarray(values if values is not None else [], dtype=bool)
    if array.size == size:
        return array
    if array.size == 0:
        return np.zeros(size, dtype=bool)
    if array.size < size:
        array = np.resize(array, size)
    else:
        array = array[:size]
    return array.astype(bool)


def _resolve_odd_even(labels: Any, size: int) -> list[str | None]:
    """Normalize odd/even tags to fixed-length list."""

    if not isinstance(labels, list | tuple):
        labels = []
    normalized: list[str | None] = [None] * size
    for idx in range(min(size, len(labels))):
        label = labels[idx]
        if label in {"odd", "even"}:
            normalized[idx] = str(label)
    return normalized


def _frequency_series(
    flux: np.ndarray,
    quantize: bool,
) -> np.ndarray:
    """Map normalized flux to an audible frequency band."""

    if flux.size == 0:
        return np.array([], dtype=float)

    mean = float(np.mean(flux))
    std = float(np.std(flux))
    if std <= 0:
        std = 1e-6

    z_scores = (flux - mean) / std
    z_scores = np.clip(z_scores, -3.0, 3.0)
    freqs = 220.0 + ((z_scores + 3.0) / 6.0) * (880.0 - 220.0)

    if quantize:
        quantize_vec = np.vectorize(_quantize_frequency)
        freqs = quantize_vec(freqs)

    return freqs


def _amplitude_series(
    in_transit: np.ndarray,
    secondary_mask: np.ndarray,
) -> np.ndarray:
    """Build amplitude weights for each sample."""

    base = np.full(in_transit.shape, 0.18, dtype=float)
    base[in_transit] += 0.15
    base[secondary_mask] += 0.08
    return np.clip(base, 0.08, 0.65)


def _segment_samples(length: int, speed: float) -> tuple[int, int]:
    """Compute samples per data point and total samples."""

    safe_speed = clamp(speed, 0.25, 4.0)
    duration = max(_BASE_DURATION / safe_speed, _MIN_DURATION)
    per_point = max(1, int(round(duration * SAMPLE_RATE)))
    total = max(1, per_point * max(1, length))
    return per_point, total


def _render_transit_ping(
    flux: np.ndarray,
    in_transit: np.ndarray,
    secondary_mask: np.ndarray,
    events: list[dict[str, Any]],
    per_point_samples: int,
    total_samples: int,
    speed: float,
) -> np.ndarray:
    """Render the baseline tone with per-event pings."""

    samples = np.zeros(total_samples, dtype=float)
    base_phase = 0.0
    base_freq = 440.0
    base_amp = 0.12
    base_increment = 2 * math.pi * base_freq / SAMPLE_RATE

    secondary_phase = 0.0
    secondary_freq = 660.0
    secondary_increment = 2 * math.pi * secondary_freq / SAMPLE_RATE

    for sample_idx in range(total_samples):
        base_phase += base_increment
        samples[sample_idx] += math.sin(base_phase) * base_amp

        data_idx = min(len(flux) - 1, sample_idx // per_point_samples)
        if secondary_mask[data_idx]:
            secondary_phase += secondary_increment
            samples[sample_idx] += math.sin(secondary_phase) * 0.08

    ping_samples = max(int(SAMPLE_RATE * 0.1 / clamp(speed, 0.25, 4.0)), 1)
    ping_freq = 880.0
    ping_increment = 2 * math.pi * ping_freq / SAMPLE_RATE

    for event in events:
        start_index = int(event.get("start_index", 0))
        start_sample = int(clamp(start_index * per_point_samples, 0, total_samples - 1))
        depth = float(abs(event.get("depth", 0.0)))
        snr = float(abs(event.get("snr", 0.0)))
        amplitude = clamp(snr / 5 if snr > 0 else depth * 40, 0.2, 0.8)

        ping_phase = 0.0
        for offset in range(ping_samples):
            idx = start_sample + offset
            if idx >= total_samples:
                break
            ping_phase += ping_increment
            envelope = math.exp(-3 * (offset / ping_samples))
            samples[idx] += math.sin(ping_phase) * amplitude * envelope

    max_val = np.max(np.abs(samples))
    if max_val > 0:
        samples /= max_val * 1.05

    return samples.astype(np.float32)


def _render_flux_pitch(
    flux: np.ndarray,
    freqs: np.ndarray,
    amplitudes: np.ndarray,
    per_point_samples: int,
    total_samples: int,
) -> np.ndarray:
    """Render flux-to-pitch melody."""

    samples = np.zeros(total_samples, dtype=float)
    phase = 0.0

    for sample_idx in range(total_samples):
        data_idx = min(len(flux) - 1, sample_idx // per_point_samples)
        freq = freqs[data_idx]
        amp = amplitudes[data_idx]
        phase += 2 * math.pi * freq / SAMPLE_RATE
        samples[sample_idx] += math.sin(phase) * amp

    max_val = np.max(np.abs(samples))
    if max_val > 0:
        samples /= max_val * 1.05

    return samples.astype(np.float32)


def _render_odd_even(
    flux: np.ndarray,
    freqs: np.ndarray,
    amplitudes: np.ndarray,
    odd_even: list[str | None],
    per_point_samples: int,
    total_samples: int,
    stereo: bool,
) -> np.ndarray:
    """Render stereo panorama that alternates odd/even transits."""

    if stereo:
        samples = np.zeros((total_samples, 2), dtype=float)
        phase = 0.0
        for sample_idx in range(total_samples):
            data_idx = min(len(flux) - 1, sample_idx // per_point_samples)
            freq = freqs[data_idx]
            amp = amplitudes[data_idx]
            phase += 2 * math.pi * freq / SAMPLE_RATE
            value = math.sin(phase) * amp

            label = odd_even[data_idx] if data_idx < len(odd_even) else None
            pan = 0.5
            if label == "odd":
                pan = 0.25
            elif label == "even":
                pan = 0.75

            left_weight = 1 - pan
            right_weight = pan
            samples[sample_idx, 0] += value * left_weight
            samples[sample_idx, 1] += value * right_weight

        max_val = np.max(np.abs(samples))
        if max_val > 0:
            samples /= max_val * 1.05

        return samples.astype(np.float32)

    samples_mono = np.zeros(total_samples, dtype=float)
    phase = 0.0
    for sample_idx in range(total_samples):
        data_idx = min(len(flux) - 1, sample_idx // per_point_samples)
        freq = freqs[data_idx]
        amp = amplitudes[data_idx]
        phase += 2 * math.pi * freq / SAMPLE_RATE
        value = math.sin(phase) * amp
        samples_mono[sample_idx] += value

    max_val = np.max(np.abs(samples_mono))
    if max_val > 0:
        samples_mono /= max_val * 1.05

    return samples_mono.astype(np.float32)


def render_waveform(
    series: dict[str, Any],
    mode: SonifyMode,
    speed: float,
    quantize: bool,
    stereo: bool,
) -> np.ndarray:
    """Render waveform samples for the given series and mode."""

    flux = np.asarray(series.get("flux", []), dtype=float)
    if flux.size == 0:
        raise ValueError("No flux samples available for sonification")

    in_transit = _prepare_boolean_array(series.get("in_transit"), flux.size)
    secondary_mask = _prepare_boolean_array(series.get("secondary_mask"), flux.size)
    odd_even = _resolve_odd_even(series.get("odd_even"), flux.size)
    events = list(series.get("events", []))

    per_point_samples, total_samples = _segment_samples(len(flux), speed)

    if mode == SonifyMode.TRANSIT_PING:
        return _render_transit_ping(
            flux,
            in_transit,
            secondary_mask,
            events,
            per_point_samples,
            total_samples,
            speed,
        )

    freqs = _frequency_series(flux, quantize)
    amplitudes = _amplitude_series(in_transit, secondary_mask)

    if mode == SonifyMode.FLUX_PITCH:
        return _render_flux_pitch(
            flux,
            freqs,
            amplitudes,
            per_point_samples,
            total_samples,
        )

    use_stereo = bool(stereo)
    samples = _render_odd_even(
        flux,
        freqs,
        amplitudes,
        odd_even,
        per_point_samples,
        total_samples,
        use_stereo,
    )
    return samples


def to_wav_bytes(samples: np.ndarray) -> bytes:
    """Serialize numpy samples to 16-bit PCM WAV."""

    buffer = io.BytesIO()
    n_channels = 2 if samples.ndim == 2 else 1

    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(n_channels)
        wav_file.setsampwidth(2)  # 16-bit PCM
        wav_file.setframerate(SAMPLE_RATE)

        audio = samples
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)
        audio = np.clip(audio, -1.0, 1.0)
        audio_int16 = np.int16(audio * 32767)
        wav_file.writeframes(audio_int16.reshape(-1).tobytes())

    return buffer.getvalue()


def generate_wav_bytes(
    series: dict[str, Any],
    mode: SonifyMode,
    speed: float,
    quantize: bool,
    stereo: bool,
) -> bytes:
    """Generate a WAV byte stream for the requested sonification."""

    samples = render_waveform(series, mode, speed, quantize, stereo)
    return to_wav_bytes(samples)
