"use client";

import React from "react";
import { Play, Square, Volume2, Settings2, Headphones, Waves } from "lucide-react";

const TAU = Math.PI * 2;
const BASE_DURATION_SECONDS = 12;

export type SonificationMode = "transit-ping" | "flux-pitch" | "odd-even";

type OddEvenTag = "odd" | "even" | null;

export type SonificationData = {
  phase: number[];
  flux: number[];
  inTransit: boolean[];
  oddEven?: OddEvenTag[];
  secondary?: boolean[];
};

type SonificationPanelProps = {
  data: SonificationData;
};

type SonificationOptions = {
  mode: SonificationMode;
  quantize: boolean;
  speed: number;
  includeSecondary: boolean;
};

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

const PENTATONIC_MIDI = [60, 62, 64, 67, 69, 72, 74, 76];

const midiToFrequency = (midi: number) => 440 * Math.pow(2, (midi - 69) / 12);

const quantizeToPentatonic = (frequency: number) => {
  const midi = 69 + 12 * Math.log2(frequency / 440);
  let closestMidi = PENTATONIC_MIDI[0];
  let smallestDistance = Math.abs(midi - closestMidi);

  for (const candidate of PENTATONIC_MIDI) {
    const distance = Math.abs(midi - candidate);
    if (distance < smallestDistance) {
      smallestDistance = distance;
      closestMidi = candidate;
    }
  }

  return midiToFrequency(closestMidi);
};

const mapFluxToFrequency = (
  flux: number,
  minFlux: number,
  maxFlux: number,
  quantize: boolean
) => {
  const fLow = 220;
  const fHigh = 880;
  const span = fHigh - fLow;
  const clampedFlux = clamp(flux, minFlux, maxFlux);
  const normalized = maxFlux - minFlux < 1e-6 ? 0.5 : (clampedFlux - minFlux) / (maxFlux - minFlux);
  const frequency = fLow + span * normalized;
  return quantize ? quantizeToPentatonic(frequency) : frequency;
};

const buildSegments = (data: SonificationData) => {
  const segments: { startIndex: number; type: "primary" | "secondary" }[] = [];
  const length = data.inTransit.length;
  let currentType: "primary" | "secondary" | null = null;

  for (let i = 0; i < length; i += 1) {
    const isSecondary = data.secondary?.[i] ?? false;
    const isPrimary = data.inTransit[i];
    const type = isSecondary ? "secondary" : isPrimary ? "primary" : null;

    if (type && type !== currentType) {
      segments.push({ startIndex: i, type });
      currentType = type;
    } else if (!type) {
      currentType = null;
    }
  }

  return segments;
};

const generateSonificationBuffer = (
  context: AudioContext,
  data: SonificationData,
  options: SonificationOptions
) => {
  const { mode, quantize, speed, includeSecondary } = options;
  const hasOddEven = mode === "odd-even" && Boolean(data.oddEven?.length);
  const channels = hasOddEven ? 2 : 1;
  const duration = Math.max(3, BASE_DURATION_SECONDS / speed);
  const sampleRate = context.sampleRate;
  const totalSamples = Math.max(1, Math.floor(sampleRate * duration));
  const buffer = context.createBuffer(channels, totalSamples, sampleRate);

  const fluxValues = data.flux;
  if (!fluxValues.length) {
    return { buffer, duration };
  }

  const minFlux = Math.min(...fluxValues);
  const maxFlux = Math.max(...fluxValues);
  const samplesPerPoint = totalSamples / fluxValues.length;

  for (let sampleIndex = 0; sampleIndex < totalSamples; sampleIndex += 1) {
    const pointPosition = sampleIndex / samplesPerPoint;
    let pointIndex = Math.floor(pointPosition);
    if (pointIndex >= fluxValues.length) {
      pointIndex = fluxValues.length - 1;
    }
    const progress = pointPosition - pointIndex;
    const time = sampleIndex / sampleRate;

    const flux = fluxValues[pointIndex];
    const inTransit = data.inTransit[pointIndex] ?? false;
    const isSecondary = includeSecondary && (data.secondary?.[pointIndex] ?? false);
    const oddEvenTag = data.oddEven?.[pointIndex] ?? null;

    const smoothEnvelope = 0.5 - 0.5 * Math.cos(Math.min(Math.PI, Math.PI * progress));

    if (mode === "odd-even" && hasOddEven) {
      const leftChannel = buffer.getChannelData(0);
      const rightChannel = buffer.getChannelData(1);
      const frequency = mapFluxToFrequency(flux, minFlux, maxFlux, quantize);
      const baseTone = Math.sin(TAU * frequency * time) * 0.22 * smoothEnvelope;
      const pingEnvelope = inTransit ? Math.exp(-progress * 8) : 0;
      const ping = inTransit ? Math.sin(TAU * 880 * time) * 0.18 * pingEnvelope : 0;
      const pan = oddEvenTag === "odd" ? 0.8 : oddEvenTag === "even" ? 0.2 : 0.5;
      const leftWeight = clamp(pan, 0, 1);
      const rightWeight = 1 - leftWeight;
      let leftValue = baseTone * leftWeight + ping * leftWeight;
      let rightValue = baseTone * rightWeight + ping * rightWeight;

      if (isSecondary) {
        const triangle = 2 * Math.abs(((time * 660) % 1) - 0.5) - 1;
        leftValue += triangle * 0.12 * smoothEnvelope;
        rightValue += triangle * 0.12 * smoothEnvelope;
      }

      leftChannel[sampleIndex] += clamp(leftValue, -1, 1);
      rightChannel[sampleIndex] += clamp(rightValue, -1, 1);
      continue;
    }

    const channelData = buffer.getChannelData(0);

    if (mode === "transit-ping") {
      let value = Math.sin(TAU * 440 * time) * 0.2;

      if (inTransit) {
        const depth = Math.max(0, 1 - flux);
        const pingAmp = clamp(0.25 + depth * 3, 0, 0.8);
        const envelope = Math.exp(-progress * 10);
        value += Math.sin(TAU * 880 * time) * pingAmp * envelope;
      }

      if (isSecondary) {
        const triangle = 2 * Math.abs(((time * 660) % 1) - 0.5) - 1;
        value += triangle * 0.15 * smoothEnvelope;
      }

      channelData[sampleIndex] = clamp(value, -1, 1);
      continue;
    }

    const frequency = mapFluxToFrequency(flux, minFlux, maxFlux, quantize);
    const value = Math.sin(TAU * frequency * time) * (0.25 + (inTransit ? 0.07 : 0)) * smoothEnvelope;
    let finalValue = value;

    if (isSecondary) {
      const triangle = 2 * Math.abs(((time * 520) % 1) - 0.5) - 1;
      finalValue += triangle * 0.12 * smoothEnvelope;
    }

    channelData[sampleIndex] = clamp(finalValue, -1, 1);
  }

  return { buffer, duration };
};

const SonificationPanel: React.FC<SonificationPanelProps> = ({ data }) => {
  const [mode, setMode] = React.useState<SonificationMode>("transit-ping");
  const [isPlaying, setIsPlaying] = React.useState(false);
  const [volume, setVolume] = React.useState(0.7);
  const [speed, setSpeed] = React.useState(1);
  const [quantize, setQuantize] = React.useState(false);
  const [includeSecondary, setIncludeSecondary] = React.useState(true);
  const [supportsHaptics, setSupportsHaptics] = React.useState(false);
  const [hapticsEnabled, setHapticsEnabled] = React.useState(false);

  const audioContextRef = React.useRef<AudioContext | null>(null);
  const sourceRef = React.useRef<AudioBufferSourceNode | null>(null);
  const gainRef = React.useRef<GainNode | null>(null);
  const vibrationTimeoutsRef = React.useRef<number[]>([]);

  const hasOddEven = React.useMemo(() => {
    if (!data.oddEven?.length) {
      return false;
    }
    const hasOdd = data.oddEven.some(tag => tag === "odd");
    const hasEven = data.oddEven.some(tag => tag === "even");
    return hasOdd && hasEven;
  }, [data.oddEven]);

  const hasSecondary = React.useMemo(() => data.secondary?.some(Boolean) ?? false, [data.secondary]);

  React.useEffect(() => {
    setIncludeSecondary(hasSecondary);
  }, [hasSecondary]);

  React.useEffect(() => {
    setSupportsHaptics(typeof navigator !== "undefined" && typeof navigator.vibrate === "function");
  }, []);

  const clearHapticTimeouts = React.useCallback(() => {
    vibrationTimeoutsRef.current.forEach(timeoutId => window.clearTimeout(timeoutId));
    vibrationTimeoutsRef.current = [];
  }, []);

  const stopPlayback = React.useCallback(() => {
    if (sourceRef.current) {
      try {
        sourceRef.current.stop();
      } catch {
        // No-op if already stopped
      }
      sourceRef.current.disconnect();
      sourceRef.current = null;
    }

    if (gainRef.current) {
      gainRef.current.disconnect();
      gainRef.current = null;
    }

    clearHapticTimeouts();
    setIsPlaying(false);
  }, [clearHapticTimeouts]);

  const ensureAudioContext = React.useCallback(() => {
    if (!audioContextRef.current) {
      audioContextRef.current = new AudioContext();
    }
    return audioContextRef.current;
  }, []);

  const scheduleHaptics = React.useCallback(
    (duration: number) => {
      if (!supportsHaptics || !hapticsEnabled) {
        return;
      }

      const segments = buildSegments(data);
      if (!segments.length) {
        return;
      }

      const msPerPoint = (duration / data.inTransit.length) * 1000;
      segments.forEach(segment => {
        const delay = segment.startIndex * msPerPoint;
        const pattern = segment.type === "secondary" ? [0, 40, 80, 40] : [0, 60, 150];
        const timeoutId = window.setTimeout(() => {
          navigator.vibrate?.(pattern);
        }, delay);
        vibrationTimeoutsRef.current.push(timeoutId);
      });
    },
    [data, hapticsEnabled, supportsHaptics]
  );

  const handlePlay = async () => {
    if (isPlaying) {
      stopPlayback();
      return;
    }

    const context = ensureAudioContext();
    if (context.state === "suspended") {
      await context.resume();
    }

    const { buffer, duration } = generateSonificationBuffer(context, data, {
      mode,
      quantize,
      speed,
      includeSecondary: includeSecondary && hasSecondary,
    });

    const source = context.createBufferSource();
    const gain = context.createGain();
    source.buffer = buffer;
    gain.gain.setValueAtTime(volume, context.currentTime);
    source.connect(gain);
    gain.connect(context.destination);
    sourceRef.current = source;
    gainRef.current = gain;

    source.start(context.currentTime + 0.05);
    setIsPlaying(true);
    scheduleHaptics(duration);

    source.onended = () => {
      clearHapticTimeouts();
      setIsPlaying(false);
    };
  };

  React.useEffect(() => {
    return () => {
      stopPlayback();
      clearHapticTimeouts();
      if (audioContextRef.current) {
        audioContextRef.current.close();
      }
    };
  }, [clearHapticTimeouts, stopPlayback]);

  React.useEffect(() => {
    if (gainRef.current && audioContextRef.current) {
      const context = audioContextRef.current;
      gainRef.current.gain.setTargetAtTime(volume, context.currentTime + 0.01, 0.05);
    }
  }, [volume]);

  React.useEffect(() => {
    if (isPlaying) {
      stopPlayback();
    }
  }, [mode, quantize, speed, includeSecondary, isPlaying, stopPlayback]);

  return (
    <div className="bg-black/30 rounded-lg p-6 border border-white/5 space-y-6">
      <div className="flex items-center gap-2">
        <Waves className="w-5 h-5 text-purple-300" />
        <h4 className="text-lg font-semibold text-white">Sound</h4>
      </div>

      <p className="text-sm text-slate-300 leading-relaxed">
        Translate the light curve into audio. Hear transits as pings, turn flux into melody, and split odd/even events
        across stereo for eclipsing binary checks.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <label className="flex flex-col gap-2">
          <span className="text-sm font-medium text-slate-200">Mode</span>
          <select
            value={mode}
            onChange={event => setMode(event.target.value as SonificationMode)}
            className="bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-white"
          >
            <option value="transit-ping">Transit Ping</option>
            <option value="flux-pitch">Flux → Pitch Melody</option>
            <option value="odd-even" disabled={!hasOddEven}>
              Odd / Even Stereo {hasOddEven ? "" : "(data unavailable)"}
            </option>
          </select>
        </label>

        <label className="flex flex-col gap-2">
          <span className="text-sm font-medium text-slate-200">Playback Speed</span>
          <select
            value={speed}
            onChange={event => setSpeed(Number(event.target.value))}
            className="bg-black/40 border border-white/10 rounded-lg px-3 py-2 text-white"
          >
            <option value={1}>1× (12s)</option>
            <option value={2}>2× (6s)</option>
          </select>
        </label>

        <label className="flex flex-col gap-2">
          <span className="text-sm font-medium text-slate-200 flex items-center gap-2">
            <Volume2 className="w-4 h-4" /> Volume
          </span>
          <input
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={volume}
            onChange={event => setVolume(Number(event.target.value))}
            className="accent-purple-400"
          />
        </label>

        <label className="flex items-center gap-3 text-sm text-slate-200">
          <input
            type="checkbox"
            checked={quantize}
            onChange={event => setQuantize(event.target.checked)}
            className="h-4 w-4 rounded border-white/20 bg-black/40"
          />
          Quantize to pentatonic scale (pleasant chords)
        </label>

        {hasSecondary && (
          <label className="flex items-center gap-3 text-sm text-slate-200">
            <input
              type="checkbox"
              checked={includeSecondary}
              onChange={event => setIncludeSecondary(event.target.checked)}
              className="h-4 w-4 rounded border-white/20 bg-black/40"
            />
            Secondary eclipse alarm (alternate timbre)
          </label>
        )}

        {supportsHaptics && (
          <label className="flex items-center gap-3 text-sm text-slate-200">
            <input
              type="checkbox"
              checked={hapticsEnabled}
              onChange={event => setHapticsEnabled(event.target.checked)}
              className="h-4 w-4 rounded border-white/20 bg-black/40"
            />
            Mobile vibration cues for transit windows
          </label>
        )}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={handlePlay}
          className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg text-white font-medium"
        >
          {isPlaying ? (
            <>
              <Square className="w-4 h-4" /> Stop
            </>
          ) : (
            <>
              <Play className="w-4 h-4" /> Hear transit
            </>
          )}
        </button>

        <div className="flex items-center gap-2 text-xs text-slate-300 uppercase tracking-wider">
          <Settings2 className="w-4 h-4" />
          <span>
            Stereo ready • {Math.round(BASE_DURATION_SECONDS / speed)}s render • Sampled at
            {" "}
            {audioContextRef.current?.sampleRate ?? 44100} Hz
          </span>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-300">
          <Headphones className="w-4 h-4" /> Use headphones to hear odd/even separation
        </div>
      </div>
    </div>
  );
};

export default SonificationPanel;
