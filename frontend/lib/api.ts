/**
 * API configuration and client for ExoSense backend
 */

// API Base URL - automatically detects environment
const getApiUrl = (): string => {
  // In production, use the Google Cloud Run deployment URL
  if (process.env.NODE_ENV === 'production') {
    return process.env.NEXT_PUBLIC_API_URL || 'https://exosense-api-PROJECT_ID.a.run.app';
  }
  
  // In development, use local API
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
};

export const API_BASE_URL = getApiUrl();

export interface AnalysisResult {
  exoplanet_detected: boolean;
  confidence: number;
  transit_depth: number;
  orbital_period: number;
  classification: string;
  analysis_id: string;
}

export interface AnalysisResponse {
  success: boolean;
  data: AnalysisResult;
  message?: string;
}

/**
 * Upload and analyze a light curve file
 */
export async function analyzeFile(file: File): Promise<AnalysisResponse> {
  const formData = new FormData();
  formData.append('file', file);

  try {
    const response = await fetch(`${API_BASE_URL}/analyze/`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      success: true,
      data: {
        exoplanet_detected: data.result?.exoplanet_detected || false,
        confidence: data.result?.confidence || 0,
        transit_depth: data.result?.transit_depth || 0,
        orbital_period: data.result?.orbital_period || 0,
        classification: data.result?.classification || 'unknown',
        analysis_id: data.analysis_id || 'unknown',
      },
    };
  } catch (error) {
    console.error('API Error:', error);
    return {
      success: false,
      data: {
        exoplanet_detected: false,
        confidence: 0,
        transit_depth: 0,
        orbital_period: 0,
        classification: 'error',
        analysis_id: 'error',
      },
      message: error instanceof Error ? error.message : 'Unknown error occurred',
    };
  }
}

/**
 * Generate PDF report for analysis
 */
export async function generateReport(analysisId: string): Promise<{ success: boolean; reportId?: string; error?: string }> {
  try {
    const response = await fetch(`${API_BASE_URL}/report/generate`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        analysis_id: analysisId,
        include_plots: true,
        format: 'pdf',
      }),
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      success: true,
      reportId: data.report_id,
    };
  } catch (error) {
    console.error('Report Generation Error:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Unknown error occurred',
    };
  }
}

/**
 * Check API health
 */
export async function checkApiHealth(): Promise<{ healthy: boolean; message?: string }> {
  try {
    const response = await fetch(`${API_BASE_URL}/healthz`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      healthy: data.status === 'ok',
      message: data.message,
    };
  } catch (error) {
    console.error('Health Check Error:', error);
    return {
      healthy: false,
      message: error instanceof Error ? error.message : 'API unreachable',
    };
  }
}