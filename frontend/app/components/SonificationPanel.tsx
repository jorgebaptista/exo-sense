"use client";

import React from "react";

export type SonificationMode = "transit-ping" | "flux-pitch";

export interface LightCurvePoint {
  time: number;
  flux: number;
  inTransit: boolean;
}

interface SonificationPanelProps {
  points: LightCurvePoint[];
  durationSeconds?: number;
}

const DEFAULT_DURATION_SECONDS = 12;
const SAMPLE_RATE = 16000;
const BASE_TONE_FREQUENCY = 440;
const PING_FREQUENCY = 880;
const MIN_MELODY_FREQUENCY = 220;
const MAX_MELODY_FREQUENCY = 880;

const PENTATONIC_STEPS = new Set([0, 2, 4, 7, 9]);

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function mapToPentatonicFrequency(frequency: number) {
  const midiValue = 69 + 12 * Math.log2(frequency / 440);
  const lowerMidi = Math.floor(midiValue);
  const upperMidi = Math.ceil(midiValue);

  const findNearest = (start: number, direction: 1 | -1) => {
    let candidate = start;
    while (!PENTATONIC_STEPS.has((candidate % 12 + 12) % 12)) {
      candidate += direction;
    }
    return candidate;
  };

  const lowerCandidate = findNearest(lowerMidi, -1);
  const upperCandidate = findNearest(upperMidi, 1);

  const lowerDiff = Math.abs(lowerCandidate - midiValue);
  const upperDiff = Math.abs(upperCandidate - midiValue);
  const chosenMidi = lowerDiff <= upperDiff ? lowerCandidate : upperCandidate;

  return 440 * Math.pow(2, (chosenMidi - 69) / 12);
}

function generateTransitPingBuffer(
  ctx: AudioContext,
  points: LightCurvePoint[],
  durationSeconds: number,
  volume: number
) {
  const frameCount = Math.floor(durationSeconds * SAMPLE_RATE);
  const buffer = ctx.createBuffer(1, frameCount, SAMPLE_RATE);
  const channel = buffer.getChannelData(0);

  const baseAmplitude = 0.12 * volume;
  for (let i = 0; i < frameCount; i += 1) {
    const t = i / SAMPLE_RATE;
    channel[i] = Math.sin(2 * Math.PI * BASE_TONE_FREQUENCY * t) * baseAmplitude;
  }

  if (!points.length) {
    return buffer;
  }

  const sampleDuration = durationSeconds / points.length;
  const depths = points.map(point => clamp(1 - point.flux, 0, 1));
  const maxDepth = depths.reduce((acc, val) => Math.max(acc, val), 0.0001);

  points.forEach((point, index) => {
    if (!point.inTransit) {
      return;
    }

    const depthScale = clamp(depths[index] / maxDepth, 0.2, 1);
    const startSample = Math.floor(index * sampleDuration * SAMPLE_RATE);
    const endSample = Math.min(frameCount, Math.floor((index + 1) * sampleDuration * SAMPLE_RATE));
    const pingAmplitude = 0.65 * volume * depthScale;

    for (let i = startSample; i < endSample; i += 1) {
      const t = i / SAMPLE_RATE;
      const localTime = (i - startSample) / SAMPLE_RATE;
      const envelope = Math.exp(-16 * localTime);
      channel[i] += Math.sin(2 * Math.PI * PING_FREQUENCY * t) * pingAmplitude * envelope;
    }
  });

  for (let i = 0; i < frameCount; i += 1) {
    channel[i] = clamp(channel[i], -1, 1);
  }

  return buffer;
}

function generateFluxPitchBuffer(
  ctx: AudioContext,
  points: LightCurvePoint[],
  durationSeconds: number,
  volume: number,
  quantize: boolean
) {
  const frameCount = Math.floor(durationSeconds * SAMPLE_RATE);
  const buffer = ctx.createBuffer(1, frameCount, SAMPLE_RATE);
  const channel = buffer.getChannelData(0);

  if (!points.length) {
    return buffer;
  }

  const sampleDuration = durationSeconds / points.length;
  const fluxValues = points.map(point => point.flux);
  const minFlux = Math.min(...fluxValues);
  const maxFlux = Math.max(...fluxValues);
  const fluxRange = maxFlux - minFlux || 1;
  const amplitude = 0.35 * volume;

  let phase = 0;

  for (let idx = 0; idx < points.length; idx += 1) {
    const point = points[idx];
    const normalized = 1 - (point.flux - minFlux) / fluxRange;
    const unclampedFreq = MIN_MELODY_FREQUENCY + normalized * (MAX_MELODY_FREQUENCY - MIN_MELODY_FREQUENCY);
    const frequency = quantize ? mapToPentatonicFrequency(unclampedFreq) : unclampedFreq;

    const startSample = Math.floor(idx * sampleDuration * SAMPLE_RATE);
    const endSample = Math.min(frameCount, Math.floor((idx + 1) * sampleDuration * SAMPLE_RATE));
    const segmentLength = Math.max(endSample - startSample, 1);

    for (let i = startSample; i < endSample; i += 1) {
      const position = i - startSample;
      const envelope = 0.5 * (1 - Math.cos((Math.PI * position) / segmentLength));
      phase += (2 * Math.PI * frequency) / SAMPLE_RATE;
      channel[i] += Math.sin(phase) * amplitude * envelope;
    }
  }

  for (let i = 0; i < frameCount; i += 1) {
    channel[i] = clamp(channel[i], -1, 1);
  }

  return buffer;
}

export function SonificationPanel({ points, durationSeconds = DEFAULT_DURATION_SECONDS }: SonificationPanelProps) {
  const [mode, setMode] = React.useState<SonificationMode>("transit-ping");
  const [quantize, setQuantize] = React.useState(false);
  const [volume, setVolume] = React.useState(0.8);
  const [speed, setSpeed] = React.useState(1);
  const [isPlaying, setIsPlaying] = React.useState(false);

  const audioContextRef = React.useRef<AudioContext | null>(null);
  const sourceNodeRef = React.useRef<AudioBufferSourceNode | null>(null);
  const gainNodeRef = React.useRef<GainNode | null>(null);

  const stopPlayback = React.useCallback(() => {
    sourceNodeRef.current?.stop();
    sourceNodeRef.current = null;
    setIsPlaying(false);
  }, []);

  React.useEffect(() => () => {
    stopPlayback();
    void audioContextRef.current?.close();
  }, [stopPlayback]);

  const ensureAudioContext = React.useCallback(async () => {
    if (!audioContextRef.current) {
      if (typeof window === "undefined") {
        throw new Error("AudioContext is not available during server render");
      }

      const AudioContextConstructor =
        window.AudioContext || (window as Window & { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;

      if (!AudioContextConstructor) {
        throw new Error("Web Audio API not supported in this browser");
      }

      audioContextRef.current = new AudioContextConstructor();
    }

    const context = audioContextRef.current;
    if (context.state === "suspended") {
      await context.resume();
    }

    return context;
  }, []);

  const handlePlay = React.useCallback(async () => {
    if (!points.length) {
      return;
    }

    if (isPlaying) {
      stopPlayback();
      return;
    }

    const context = await ensureAudioContext();
    const totalDuration = durationSeconds / speed;

    const buffer =
      mode === "transit-ping"
        ? generateTransitPingBuffer(context, points, totalDuration, volume)
        : generateFluxPitchBuffer(context, points, totalDuration, volume, quantize);

    const source = context.createBufferSource();
    source.buffer = buffer;

    const gainNode = context.createGain();
    gainNode.gain.value = volume;

    source.connect(gainNode);
    gainNode.connect(context.destination);

    source.onended = () => {
      setIsPlaying(false);
      sourceNodeRef.current = null;
    };

    gainNodeRef.current = gainNode;
    sourceNodeRef.current = source;

    source.start(0);
    setIsPlaying(true);
  }, [ensureAudioContext, durationSeconds, isPlaying, mode, points, quantize, speed, stopPlayback, volume]);

  const handleVolumeChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const value = Number(event.target.value);
    setVolume(value);
    if (gainNodeRef.current) {
      gainNodeRef.current.gain.linearRampToValueAtTime(value, (audioContextRef.current?.currentTime ?? 0) + 0.05);
    }
  };

  const handleModeChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setMode(event.target.value as SonificationMode);
    if (isPlaying) {
      stopPlayback();
    }
  };

  const handleQuantizeToggle = (event: React.ChangeEvent<HTMLInputElement>) => {
    setQuantize(event.target.checked);
    if (isPlaying) {
      stopPlayback();
    }
  };

  const handleSpeedChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setSpeed(Number(event.target.value));
    if (isPlaying) {
      stopPlayback();
    }
  };

  return (
    <div className="mt-8 rounded-2xl border border-white/10 bg-black/40 p-6 text-white">
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
        <div>
          <h4 className="text-lg font-semibold">Hear the Transit</h4>
          <p className="text-sm text-slate-300">
            Turn the phase-folded light curve into sound. Choose a mode and press play to listen.
          </p>
        </div>
        <button
          type="button"
          onClick={handlePlay}
          className="flex items-center gap-2 self-start rounded-xl bg-purple-600 px-4 py-2 font-medium transition hover:bg-purple-700"
        >
          {isPlaying ? (
            <>
              <span aria-hidden className="text-lg leading-none">
                ❚❚
              </span>
              Stop
            </>
          ) : (
            <>
              <span aria-hidden className="text-lg leading-none">
                ▶
              </span>
              Play
            </>
          )}
        </button>
      </div>

      <div className="mt-6 grid gap-6 md:grid-cols-3">
        <label className="flex flex-col gap-2">
          <span className="text-sm font-medium text-slate-200">Mode</span>
          <select
            value={mode}
            onChange={handleModeChange}
            className="rounded-lg border border-white/10 bg-black/60 px-3 py-2 text-sm"
          >
            <option value="transit-ping">Transit Ping (base tone + pings)</option>
            <option value="flux-pitch">Flux → Pitch Melody</option>
          </select>
        </label>

        <label className="flex flex-col gap-2">
          <span className="text-sm font-medium text-slate-200">Playback Speed</span>
          <select
            value={speed}
            onChange={handleSpeedChange}
            className="rounded-lg border border-white/10 bg-black/60 px-3 py-2 text-sm"
          >
            <option value={0.75}>0.75× (detailed)</option>
            <option value={1}>1×</option>
            <option value={1.5}>1.5×</option>
            <option value={2}>2×</option>
          </select>
        </label>

        <label className="flex flex-col gap-2">
          <span className="text-sm font-medium text-slate-200">Volume</span>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={volume}
            onChange={handleVolumeChange}
            className="accent-purple-500"
          />
        </label>
      </div>

      <label className="mt-6 flex items-center gap-3 text-sm text-slate-200">
        <input
          type="checkbox"
          checked={quantize}
          onChange={handleQuantizeToggle}
          className="h-4 w-4 rounded border-white/20 bg-black/40"
          disabled={mode !== "flux-pitch"}
        />
        <span>Quantize melody to a pentatonic scale (pleasant & demo-friendly)</span>
      </label>
    </div>
  );
}
