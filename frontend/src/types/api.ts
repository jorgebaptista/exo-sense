export type OddEvenTag = 'odd' | 'even' | null

export interface TransitEvent {
  index: number
  start_index: number
  end_index: number
  start_time: number
  end_time: number
  depth: number
  snr: number
}

export interface SonificationSeries {
  time: number[]
  flux: number[]
  phase: number[]
  phase_folded_phase: number[]
  phase_folded_flux: number[]
  in_transit: boolean[]
  odd_even: OddEvenTag[]
  secondary_mask: boolean[]
  events: TransitEvent[]
  sample_interval: number | null
  secondary_sigma: number | null
}

export interface AnalysisResult {
  exoplanet_detected: boolean
  confidence: number
  transit_depth: number | null
  orbital_period: number | null
  label: string
  reasons: string[]
}

export interface AnalysisResponse {
  analysis_id: string
  filename: string
  result: AnalysisResult
  plots: Record<string, string>
  metrics: Record<string, number>
  processing_time: number
  sonification: SonificationSeries | null
}
