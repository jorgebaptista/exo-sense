import { type SonificationSeries, type OddEvenTag } from '@/types/api'

export type SonificationMode = 'transit_ping' | 'flux_pitch' | 'odd_even'

export interface SonificationOptions {
  mode: SonificationMode
  speed: number
  quantize: boolean
  stereo: boolean
  volume: number
}

export interface RenderedAudio {
  sampleRate: number
  left: Float32Array
  right?: Float32Array
  duration: number
}

const SAMPLE_RATE = 16000
const BASE_DURATION = 0.02
const MIN_DURATION = 0.005
const PENTATONIC_STEPS = [0, 2, 4, 7, 9]

const clamp = (value: number, min: number, max: number) => Math.max(min, Math.min(max, value))

const quantizeFrequency = (freq: number) => {
  if (freq <= 0) return 220
  const midi = 69 + 12 * Math.log2(freq / 440)
  const octave = Math.floor(midi / 12)
  const withinOctave = midi - octave * 12
  const nearest = PENTATONIC_STEPS.reduce((prev, current) =>
    Math.abs(current - withinOctave) < Math.abs(prev - withinOctave) ? current : prev
  )
  const quantizedMidi = octave * 12 + nearest
  return 440 * Math.pow(2, (quantizedMidi - 69) / 12)
}

const frequencySeries = (flux: number[], quantize: boolean) => {
  if (flux.length === 0) return new Float32Array()
  const mean = flux.reduce((acc, value) => acc + value, 0) / flux.length
  const variance = flux.reduce((acc, value) => acc + Math.pow(value - mean, 2), 0) / flux.length
  const std = Math.sqrt(variance) || 1e-6
  const freqs = new Float32Array(flux.length)
  flux.forEach((value, index) => {
    const z = clamp((value - mean) / std, -3, 3)
    const freq = 220 + ((z + 3) / 6) * (880 - 220)
    freqs[index] = quantize ? quantizeFrequency(freq) : freq
  })
  return freqs
}

const amplitudeSeries = (inTransit: boolean[], secondary: boolean[]) => {
  const amplitudes = new Float32Array(inTransit.length)
  for (let i = 0; i < inTransit.length; i += 1) {
    let value = 0.18
    if (inTransit[i]) value += 0.15
    if (secondary[i]) value += 0.08
    amplitudes[i] = clamp(value, 0.08, 0.65)
  }
  return amplitudes
}

const resolveBoolArray = (values: boolean[] | undefined, length: number) => {
  if (!values || values.length === 0) return new Array<boolean>(length).fill(false)
  if (values.length === length) return values.slice()
  if (values.length > length) return values.slice(0, length)
  return values.concat(new Array<boolean>(length - values.length).fill(false))
}

const resolveOddEven = (values: OddEvenTag[] | undefined, length: number) => {
  const resolved = new Array<OddEvenTag>(length).fill(null)
  if (!values) return resolved
  for (let i = 0; i < Math.min(length, values.length); i += 1) {
    const value = values[i]
    if (value === 'odd' || value === 'even') {
      resolved[i] = value
    }
  }
  return resolved
}

const segmentSamples = (length: number, speed: number) => {
  const safeSpeed = clamp(speed, 0.25, 4)
  const duration = Math.max(BASE_DURATION / safeSpeed, MIN_DURATION)
  const perPoint = Math.max(1, Math.round(duration * SAMPLE_RATE))
  const total = Math.max(1, perPoint * Math.max(1, length))
  return { perPoint, total }
}

const renderTransitPing = (
  series: SonificationSeries,
  perPoint: number,
  total: number,
  speed: number,
  secondary: boolean[]
) => {
  const buffer = new Float32Array(total)
  const secondaryPhaseState = { value: 0 }

  const baseIncrement = (2 * Math.PI * 440) / SAMPLE_RATE
  const secondaryIncrement = (2 * Math.PI * 660) / SAMPLE_RATE

  for (let sample = 0; sample < total; sample += 1) {
    const dataIndex = Math.min(series.flux.length - 1, Math.floor(sample / perPoint))
    const phase = baseIncrement * sample
    buffer[sample] += Math.sin(phase) * 0.12
    if (secondary[dataIndex]) {
      secondaryPhaseState.value += secondaryIncrement
      buffer[sample] += Math.sin(secondaryPhaseState.value) * 0.08
    }
  }

  const pingSamples = Math.max(Math.floor((SAMPLE_RATE * 0.1) / clamp(speed, 0.25, 4)), 1)
  const pingIncrement = (2 * Math.PI * 880) / SAMPLE_RATE

  series.events.forEach((event: SonificationSeries['events'][number]) => {
    const startSample = Math.min(total - 1, Math.max(0, event.start_index * perPoint))
    const depth = Math.abs(event.depth)
    const snr = Math.abs(event.snr)
    const amplitude = clamp(snr > 0 ? snr / 5 : depth * 40, 0.2, 0.8)
    let pingPhase = 0
    for (let offset = 0; offset < pingSamples; offset += 1) {
      const idx = startSample + offset
      if (idx >= total) break
      pingPhase += pingIncrement
      const envelope = Math.exp(-3 * (offset / pingSamples))
      buffer[idx] += Math.sin(pingPhase) * amplitude * envelope
    }
  })

  let max = 0
  for (let i = 0; i < buffer.length; i += 1) {
    max = Math.max(max, Math.abs(buffer[i]))
  }
  if (max > 0) {
    for (let i = 0; i < buffer.length; i += 1) {
      buffer[i] = buffer[i] / (max * 1.05)
    }
  }

  return { left: buffer }
}

const renderFluxPitch = (
  series: SonificationSeries,
  freqs: Float32Array,
  amplitudes: Float32Array,
  perPoint: number,
  total: number
) => {
  const buffer = new Float32Array(total)
  let phase = 0
  for (let sample = 0; sample < total; sample += 1) {
    const dataIndex = Math.min(series.flux.length - 1, Math.floor(sample / perPoint))
    const freq = freqs[dataIndex]
    const amp = amplitudes[dataIndex]
    phase += (2 * Math.PI * freq) / SAMPLE_RATE
    buffer[sample] += Math.sin(phase) * amp
  }

  let max = 0
  for (let i = 0; i < buffer.length; i += 1) {
    max = Math.max(max, Math.abs(buffer[i]))
  }
  if (max > 0) {
    for (let i = 0; i < buffer.length; i += 1) {
      buffer[i] = buffer[i] / (max * 1.05)
    }
  }

  return { left: buffer }
}

const renderOddEven = (
  series: SonificationSeries,
  freqs: Float32Array,
  amplitudes: Float32Array,
  oddEven: OddEvenTag[],
  perPoint: number,
  total: number,
  stereo: boolean
) => {
  if (stereo) {
    const left = new Float32Array(total)
    const right = new Float32Array(total)
    let phase = 0
    for (let sample = 0; sample < total; sample += 1) {
      const dataIndex = Math.min(series.flux.length - 1, Math.floor(sample / perPoint))
      const freq = freqs[dataIndex]
      const amp = amplitudes[dataIndex]
      phase += (2 * Math.PI * freq) / SAMPLE_RATE
      const value = Math.sin(phase) * amp
      const tag = oddEven[dataIndex]
      let pan = 0.5
      if (tag === 'odd') pan = 0.25
      if (tag === 'even') pan = 0.75
      left[sample] += value * (1 - pan)
      right[sample] += value * pan
    }
    let max = 0
    for (let i = 0; i < total; i += 1) {
      max = Math.max(max, Math.abs(left[i]), Math.abs(right[i]))
    }
    if (max > 0) {
      const normalizer = max * 1.05
      for (let i = 0; i < total; i += 1) {
        left[i] = left[i] / normalizer
        right[i] = right[i] / normalizer
      }
    }
    return { left, right }
  }

  const mono = renderFluxPitch(series, freqs, amplitudes, perPoint, total)
  return { left: mono.left }
}

export const renderSonification = (
  series: SonificationSeries,
  options: SonificationOptions
): RenderedAudio => {
  const inTransit = resolveBoolArray(series.in_transit, series.flux.length)
  const secondary = resolveBoolArray(series.secondary_mask, series.flux.length)
  const oddEven = resolveOddEven(series.odd_even, series.flux.length)
  const { perPoint, total } = segmentSamples(series.flux.length, options.speed)

  let left: Float32Array
  let right: Float32Array | undefined

  if (options.mode === 'transit_ping') {
    const rendered = renderTransitPing(series, perPoint, total, options.speed, secondary)
    left = rendered.left
  } else {
    const freqs = frequencySeries(series.flux, options.quantize)
    const amplitudes = amplitudeSeries(inTransit, secondary)
    if (options.mode === 'flux_pitch') {
      const rendered = renderFluxPitch(series, freqs, amplitudes, perPoint, total)
      left = rendered.left
    } else {
      const rendered = renderOddEven(
        series,
        freqs,
        amplitudes,
        oddEven,
        perPoint,
        total,
        options.stereo
      )
      left = rendered.left
      right = rendered.right
    }
  }

  const volume = clamp(options.volume, 0, 1)
  for (let i = 0; i < left.length; i += 1) {
    left[i] *= volume
  }
  if (right) {
    for (let i = 0; i < right.length; i += 1) {
      right[i] *= volume
    }
  }

  return {
    sampleRate: SAMPLE_RATE,
    left,
    right,
    duration: left.length / SAMPLE_RATE
  }
}

export const AUDIO_SAMPLE_RATE = SAMPLE_RATE
