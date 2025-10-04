'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Download, Headphones, Pause, Play, Volume2, Waveform } from 'lucide-react'

import type { SonificationSeries } from '@/types/api'
import { AUDIO_SAMPLE_RATE, type SonificationMode, renderSonification } from '../utils/sonification'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000'

type Props = {
  analysisId: string
  series: SonificationSeries
}

type AudioContextConstructor = typeof AudioContext & {
  new (): AudioContext
}

export default function SonificationPanel({ analysisId, series }: Props) {
  const [mode, setMode] = useState<SonificationMode>('transit_ping')
  const [speed, setSpeed] = useState<number>(1)
  const [quantize, setQuantize] = useState<boolean>(false)
  const [stereo, setStereo] = useState<boolean>(false)
  const [volume, setVolume] = useState<number>(0.8)
  const [isPlaying, setIsPlaying] = useState<boolean>(false)
  const [duration, setDuration] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  const audioContextRef = useRef<AudioContext | null>(null)
  const sourceRef = useRef<AudioBufferSourceNode | null>(null)
  const gainRef = useRef<GainNode | null>(null)

  const stopPlayback = useCallback(() => {
    setError(null)
    if (sourceRef.current) {
      try {
        sourceRef.current.stop()
      } catch (err) {
        console.warn('Stop playback error', err)
      }
      sourceRef.current.disconnect()
      sourceRef.current = null
    }
    if (gainRef.current) {
      gainRef.current.disconnect()
      gainRef.current = null
    }
    setIsPlaying(false)
  }, [])

  useEffect(() => {
    return () => {
      stopPlayback()
      audioContextRef.current?.close().catch(() => undefined)
    }
  }, [stopPlayback])

  const secondarySummary = useMemo(() => {
    if (series.secondary_sigma && series.secondary_sigma > 0) {
      return `${series.secondary_sigma.toFixed(2)}σ secondary eclipse`
    }
    return 'No significant secondary eclipse'
  }, [series.secondary_sigma])

  const eventsSummary = useMemo(() => {
    if (!series.events.length) return 'No transits flagged'
    const firstDepth = series.events[0]?.depth ?? 0
    return `${series.events.length} transit${series.events.length > 1 ? 's' : ''} • depth ≈ ${(firstDepth * 1000).toFixed(1)} ppt`
  }, [series.events])

  const downloadUrl = useMemo(() => {
    const params = new URLSearchParams({
      analysis_id: analysisId,
      mode,
      speed: speed.toString(),
      quantize: quantize.toString(),
      stereo: stereo.toString()
    })
    return `${API_BASE_URL}/sonify/?${params.toString()}`
  }, [analysisId, mode, quantize, speed, stereo])

  const ensureAudioContext = () => {
    if (typeof window === 'undefined') return null
    if (audioContextRef.current) return audioContextRef.current
    const AnyWindow = window as typeof window & {
      webkitAudioContext?: AudioContextConstructor
    }
    const Ctor = (window.AudioContext ?? AnyWindow.webkitAudioContext) as AudioContextConstructor | undefined
    if (!Ctor) {
      setError('Web Audio API is not supported in this browser.')
      return null
    }
    audioContextRef.current = new Ctor()
    return audioContextRef.current
  }

  const handlePlay = async () => {
    if (isPlaying) {
      stopPlayback()
      return
    }

    setError(null)
    const context = ensureAudioContext()
    if (!context) return

    try {
      if (context.state === 'suspended') {
        await context.resume()
      }

      const render = renderSonification(series, {
        mode,
        speed,
        quantize,
        stereo,
        volume
      })

      setDuration(render.duration)

      const buffer = context.createBuffer(render.right ? 2 : 1, render.left.length, render.sampleRate)
      buffer.getChannelData(0).set(render.left)
      if (render.right) {
        buffer.getChannelData(1).set(render.right)
      }

      stopPlayback()

      const source = context.createBufferSource()
      source.buffer = buffer

      const gain = gainRef.current ?? context.createGain()
      gain.gain.setValueAtTime(1, context.currentTime)

      source.connect(gain)
      gain.connect(context.destination)

      sourceRef.current = source
      gainRef.current = gain

      source.onended = () => {
        setIsPlaying(false)
      }

      const startTime = context.currentTime + 0.1
      source.start(startTime)
      setIsPlaying(true)
    } catch (err) {
      console.error('Unable to start sonification', err)
      setError('Unable to play sonification audio.')
      stopPlayback()
    }
  }

  return (
    <div className="mt-8 bg-black/30 border border-white/10 rounded-2xl p-6">
      <div className="flex items-center gap-3 mb-4">
        <Waveform className="w-6 h-6 text-purple-300" />
        <div>
          <p className="text-sm uppercase tracking-wider text-purple-300">Sonification</p>
          <h4 className="text-lg font-semibold text-white">Hear the transit signature</h4>
        </div>
      </div>

      <p className="text-sm text-slate-300 mb-4">
        Map the light curve into sound. Time becomes rhythm, flux becomes pitch, and transit depth rings as a percussive ping.
      </p>

      {error && (
        <div className="mb-4 rounded-lg border border-red-500/40 bg-red-500/10 px-4 py-3 text-sm text-red-200">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <label className="flex flex-col gap-2">
          <span className="text-xs uppercase tracking-wide text-slate-300">Mode</span>
          <select
            value={mode}
            onChange={event => {
              const nextMode = event.target.value as SonificationMode
              setMode(nextMode)
              setStereo(nextMode === 'odd_even')
            }}
            className="rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-sm text-white focus:border-purple-400 focus:outline-none"
          >
            <option value="transit_ping">Transit ping (demo friendly)</option>
            <option value="flux_pitch">Flux → pitch melody</option>
            <option value="odd_even">Odd/Even stereo split</option>
          </select>
        </label>

        <label className="flex flex-col gap-2">
          <span className="text-xs uppercase tracking-wide text-slate-300">Playback speed</span>
          <select
            value={speed}
            onChange={event => setSpeed(Number(event.target.value))}
            className="rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-sm text-white focus:border-purple-400 focus:outline-none"
          >
            <option value={1}>1× (12 s)</option>
            <option value={1.5}>1.5×</option>
            <option value={2}>2×</option>
          </select>
        </label>

        <label className="flex flex-col gap-2">
          <span className="text-xs uppercase tracking-wide text-slate-300">Volume</span>
          <div className="flex items-center gap-3">
            <Volume2 className="h-4 w-4 text-purple-300" />
            <input
              type="range"
              min={0.2}
              max={1}
              step={0.05}
              value={volume}
              onChange={event => setVolume(Number(event.target.value))}
              className="flex-1 accent-purple-400"
            />
            <span className="w-10 text-right text-xs text-slate-200">{Math.round(volume * 100)}%</span>
          </div>
        </label>

        {mode === 'flux_pitch' && (
          <label className="flex items-center justify-between gap-2 rounded-lg border border-white/10 bg-black/40 px-3 py-2">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-300">Quantize</p>
              <p className="text-xs text-slate-400">Snap to pentatonic scale</p>
            </div>
            <input
              type="checkbox"
              checked={quantize}
              onChange={event => setQuantize(event.target.checked)}
              className="h-4 w-4 accent-purple-400"
            />
          </label>
        )}

        {mode === 'odd_even' && (
          <label className="flex items-center justify-between gap-2 rounded-lg border border-white/10 bg-black/40 px-3 py-2">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-300">Stereo panorama</p>
              <p className="text-xs text-slate-400">Odd transits left, even right</p>
            </div>
            <input
              type="checkbox"
              checked={stereo}
              onChange={event => setStereo(event.target.checked)}
              className="h-4 w-4 accent-purple-400"
            />
          </label>
        )}
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-4">
        <button
          type="button"
          onClick={handlePlay}
          className="inline-flex items-center gap-2 rounded-full bg-purple-500 px-5 py-2 text-sm font-semibold text-white transition hover:bg-purple-600"
        >
          {isPlaying ? (
            <>
              <Pause className="h-4 w-4" />
              Stop
            </>
          ) : (
            <>
              <Play className="h-4 w-4" />
              Play sonification
            </>
          )}
        </button>

        <a
          href={downloadUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 rounded-full border border-purple-400/60 px-5 py-2 text-sm font-semibold text-purple-200 transition hover:bg-purple-500/20"
        >
          <Download className="h-4 w-4" />
          Download WAV
        </a>
      </div>

      <div className="mt-6 grid gap-3 rounded-xl border border-white/10 bg-black/40 p-4 md:grid-cols-3">
        <div className="flex items-center gap-2 text-slate-200">
          <Headphones className="h-4 w-4 text-purple-300" />
          <span className="text-xs uppercase tracking-wide text-slate-400">Run ID</span>
          <span className="text-sm font-semibold text-white">{analysisId.slice(0, 8)}</span>
        </div>
        <div className="text-sm text-slate-200">
          <p className="text-xs uppercase tracking-wide text-slate-400">Duration</p>
          <p className="font-semibold text-white">
            {duration ? `${duration.toFixed(1)} s` : 'Play to preview duration'} • {AUDIO_SAMPLE_RATE / 1000} kHz
          </p>
        </div>
        <div className="text-sm text-slate-200">
          <p className="text-xs uppercase tracking-wide text-slate-400">Highlights</p>
          <p className="font-semibold text-white">{eventsSummary}</p>
          <p className="text-xs text-slate-400">{secondarySummary}</p>
        </div>
      </div>
    </div>
  )
}
