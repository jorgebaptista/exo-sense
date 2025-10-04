"use client";

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type {
  SonificationData,
  SonificationMode,
  SonificationSettings,
} from '../../src/types/sonification';

type IconProps = React.SVGProps<SVGSVGElement>;

const PlayIcon = ({ className, ...props }: IconProps) => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={2}
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-hidden
    {...props}
  >
    <polygon points="6 4 20 12 6 20 6 4" />
  </svg>
);

const PauseIcon = ({ className, ...props }: IconProps) => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={2}
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-hidden
    {...props}
  >
    <rect x={6} y={4} width={4} height={16} rx={1} />
    <rect x={14} y={4} width={4} height={16} rx={1} />
  </svg>
);

const SoundIcon = ({ className, ...props }: IconProps) => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={2}
    strokeLinecap="round"
    strokeLinejoin="round"
    className={className}
    aria-hidden
    {...props}
  >
    <polygon points="4 9 9 9 13 5 13 19 9 15 4 15 4 9" />
    <path d="M16.5 8.5a5 5 0 0 1 0 7" />
    <path d="M19 6a8 8 0 0 1 0 12" />
  </svg>
);

const BASE_SAMPLE_RATE = 16000;
const BASE_DURATION_SECONDS = 12;
const PING_DURATION = 0.12;
const BASE_TONE_FREQUENCY = 440;
const PING_FREQUENCY = 880;
const MIN_PITCH = 220;
const MAX_PITCH = 880;
const QUANTIZED_SCALE = [220, 247, 262, 294, 330, 392, 440, 494, 523, 587, 659, 784];

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

const mapToQuantizedFrequency = (frequency: number) => {
  const closest = QUANTIZED_SCALE.reduce<{ value: number; diff: number }>(
    (acc, note) => {
      const diff = Math.abs(note - frequency);
      if (diff < acc.diff) {
        return { value: note, diff };
      }
      return acc;
    },
    { value: QUANTIZED_SCALE[0], diff: Number.POSITIVE_INFINITY },
  );

  return closest.value;
};

const normaliseFlux = (flux: number[]) => {
  const min = Math.min(...flux);
  const max = Math.max(...flux);
  if (max - min === 0) {
    return flux.map(() => 0.5);
  }
  return flux.map((value) => (value - min) / (max - min));
};

const createAudioBuffer = (
  context: AudioContext,
  data: SonificationData,
  settings: SonificationSettings,
) => {
  const sampleCount = data.phase.length;
  if (sampleCount === 0) {
    throw new Error('Cannot generate audio for empty dataset');
  }

  const duration = BASE_DURATION_SECONDS / settings.speed;
  const sampleRate = BASE_SAMPLE_RATE;
  const totalSamples = Math.ceil(duration * sampleRate);
  const buffer = context.createBuffer(settings.mode === 'odd-even' ? 2 : 1, totalSamples, sampleRate);
  const outputL = buffer.getChannelData(0);
  const outputR = settings.mode === 'odd-even' ? buffer.getChannelData(1) : outputL;

  const timePerSample = duration / sampleCount;
  const normalisedFlux = normaliseFlux(data.flux);

  const pitchForIndex = normalisedFlux.map((value) => {
    const freq = MIN_PITCH + value * (MAX_PITCH - MIN_PITCH);
    return settings.quantize ? mapToQuantizedFrequency(freq) : freq;
  });

  for (let i = 0; i < totalSamples; i += 1) {
    const t = i / sampleRate;
    const phaseIndex = clamp(Math.floor(t / timePerSample), 0, sampleCount - 1);
    const basePhase = 2 * Math.PI * t;

    if (settings.mode === 'transit-ping') {
      const baseTone = Math.sin(basePhase * BASE_TONE_FREQUENCY) * 0.1;
      let pingContribution = 0;
      if (data.inTransitMask[phaseIndex]) {
        const start = phaseIndex * timePerSample;
        const delta = t - start;
        if (delta >= 0 && delta <= PING_DURATION) {
          const envelope = 1 - delta / PING_DURATION;
          pingContribution = Math.sin(2 * Math.PI * (t - start) * PING_FREQUENCY) * envelope * 0.6;
        }
      }
      outputL[i] = baseTone + pingContribution;
    } else {
      const frequency = pitchForIndex[phaseIndex];
      const tone = Math.sin(basePhase * frequency) * 0.25;
      if (settings.mode === 'odd-even') {
        const oddEven = data.oddEvenMask[phaseIndex] ?? 'odd';
        if (oddEven === 'odd') {
          outputL[i] = tone;
          outputR[i] = tone * 0.2;
        } else {
          outputL[i] = tone * 0.2;
          outputR[i] = tone;
        }
      } else {
        outputL[i] = tone;
      }
    }
  }

  return buffer;
};

const defaultSettings: SonificationSettings = {
  mode: 'transit-ping',
  quantize: false,
  speed: 1,
  volume: 0.8,
};

const formatModeLabel = (mode: SonificationMode) => {
  switch (mode) {
    case 'flux-pitch':
      return 'Flux → Pitch Melody';
    case 'odd-even':
      return 'Odd/Even Stereo';
    case 'transit-ping':
    default:
      return 'Transit Ping';
  }
};

export type SonificationPanelProps = {
  data: SonificationData;
};

export function SonificationPanel({ data }: SonificationPanelProps) {
  const [settings, setSettings] = useState<SonificationSettings>(defaultSettings);
  const [isPlaying, setIsPlaying] = useState(false);
  const audioContextRef = useRef<AudioContext | null>(null);
  const sourceRef = useRef<AudioBufferSourceNode | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);

  useEffect(() => () => {
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
  }, []);

  const handleStop = useCallback(() => {
    setIsPlaying(false);
    if (sourceRef.current) {
      try {
        sourceRef.current.stop();
      } catch {
        // Ignore errors when stopping an already stopped source
      }
      sourceRef.current.disconnect();
      sourceRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close().catch(() => {});
      audioContextRef.current = null;
    }
  }, []);

  const play = useCallback(async () => {
    if (isPlaying) {
      handleStop();
      return;
    }

    const context = new AudioContext();
    audioContextRef.current = context;
    const gainNode = context.createGain();
    gainNode.gain.value = settings.volume;
    gainNodeRef.current = gainNode;

    const buffer = createAudioBuffer(context, data, settings);
    const source = context.createBufferSource();
    source.buffer = buffer;
    source.connect(gainNode).connect(context.destination);
    source.onended = () => {
      setIsPlaying(false);
      handleStop();
    };
    source.start(context.currentTime + 0.1);
    sourceRef.current = source;
    setIsPlaying(true);
  }, [data, handleStop, isPlaying, settings]);

  useEffect(() => {
    if (gainNodeRef.current) {
      gainNodeRef.current.gain.linearRampToValueAtTime(
        clamp(settings.volume, 0, 1),
        (audioContextRef.current?.currentTime ?? 0) + 0.1,
      );
    }
  }, [settings.volume]);

  useEffect(() => {
    if (!isPlaying) {
      return;
    }
    handleStop();
  }, [handleStop, isPlaying, settings.mode, settings.quantize, settings.speed]);

  const sampleCount = data.phase.length;
  const estimatedDuration = useMemo(
    () => (BASE_DURATION_SECONDS / settings.speed).toFixed(1),
    [settings.speed],
  );

  return (
    <div className="mt-8 border border-purple-500/20 bg-black/40 rounded-xl p-6 text-white">
      <div className="flex items-center gap-3 mb-4">
        <SoundIcon className="w-6 h-6 text-purple-300" />
        <h4 className="text-xl font-semibold">Hear the Transit</h4>
      </div>
      <p className="text-sm text-slate-300 mb-4">
        Sonify the phase-folded light curve. Time maps directly to playback time and flux maps to
        pitch or ping loudness so you can hear the transit depth and duration.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-sm text-slate-300 mb-1" htmlFor="sonification-mode">
            Mode
          </label>
          <select
            id="sonification-mode"
            value={settings.mode}
            onChange={(event) =>
              setSettings((prev) => ({
                ...prev,
                mode: event.target.value as SonificationMode,
              }))
            }
            className="w-full rounded-lg bg-slate-900/70 border border-purple-500/30 px-3 py-2"
          >
            <option value="transit-ping">Transit Ping</option>
            <option value="flux-pitch">Flux → Pitch Melody</option>
            <option value="odd-even">Odd/Even Stereo</option>
          </select>
        </div>
        <div>
          <label className="block text-sm text-slate-300 mb-1" htmlFor="sonification-speed">
            Playback Speed
          </label>
          <select
            id="sonification-speed"
            value={settings.speed}
            onChange={(event) =>
              setSettings((prev) => ({
                ...prev,
                speed: Number(event.target.value) as 1 | 2,
              }))
            }
            className="w-full rounded-lg bg-slate-900/70 border border-purple-500/30 px-3 py-2"
          >
            <option value={1}>1× (detailed)</option>
            <option value={2}>2× (snappier)</option>
          </select>
        </div>
      </div>
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <label className="flex items-center gap-3">
          <input
            type="checkbox"
            checked={settings.quantize}
            onChange={(event) =>
              setSettings((prev) => ({
                ...prev,
                quantize: event.target.checked,
              }))
            }
            className="h-4 w-4 rounded border-purple-500/50 bg-slate-900/70"
          />
          <span className="text-sm text-slate-300">Quantize to pleasant scale</span>
        </label>
        <div className="flex items-center gap-3">
          <span className="text-sm text-slate-300">Volume</span>
          <input
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={settings.volume}
            onChange={(event) =>
              setSettings((prev) => ({
                ...prev,
                volume: Number(event.target.value),
              }))
            }
            className="w-48 accent-purple-500"
            aria-label="Sonification volume"
          />
        </div>
      </div>
      <div className="mt-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <button
          type="button"
          onClick={() => play().catch(() => handleStop())}
          className="inline-flex items-center gap-2 bg-purple-600 hover:bg-purple-700 transition-colors px-4 py-2 rounded-lg font-semibold"
        >
          {isPlaying ? (
            <>
              <PauseIcon className="w-5 h-5" />
              Stop
            </>
          ) : (
            <>
              <PlayIcon className="w-5 h-5" />
              Play
            </>
          )}
        </button>
        <div className="text-sm text-slate-400">
          <p>Samples: {sampleCount}</p>
          <p>Estimated duration: {estimatedDuration} s</p>
          <p>Mode: {formatModeLabel(settings.mode)}</p>
        </div>
      </div>
    </div>
  );
}

export default SonificationPanel;
