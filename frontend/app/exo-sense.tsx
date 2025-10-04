"use client";

import React, { useState } from 'react';
import { Upload, Search, FileText, AlertCircle, CheckCircle2, Loader2, Clock } from 'lucide-react';

import SonificationPanel from './components/SonificationPanel';
import type { AnalysisResponse } from '@/types/api';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000';

export default function ExoplanetDetector() {
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [results, setResults] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Generate random stars only on the client after mount to avoid SSR/CSR hydration mismatch
  type Star = {
    id: number;
    left: number;
    top: number;
    size: number;
    opacity: number;
    animationDelay: number;
  };

  const [stars, setStars] = React.useState<Star[]>([]);

  React.useEffect(() => {
    const generated: Star[] = Array.from({ length: 150 }, (_, i) => ({
      id: i,
      left: Math.random() * 100,
      top: Math.random() * 100,
      size: Math.random() * 2 + 1,
      opacity: Math.random() * 0.5 + 0.3,
      animationDelay: Math.random() * 3,
    }));
    setStars(generated);
  }, []);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0] ?? null;
    if (selectedFile) {
      setFile(selectedFile);
      setError(null);
      setResults(null);
    }
  };

  const handleAnalyze = async () => {
    if (!file) {
      setError('Please select a file first');
      return;
    }

    setLoading(true);
    setError(null);
    setResults(null);

    try {
      const formData = new FormData();
      formData.append('file', file);

      const response = await fetch(`${API_BASE_URL}/analyze/`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || 'Analysis failed');
      }

      const data = (await response.json()) as AnalysisResponse;
      setResults(data);
    } catch (apiError) {
      console.error(apiError);
      const message = apiError instanceof Error ? apiError.message : 'Failed to analyze data. Please try again.';
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    const droppedFile = e.dataTransfer.files?.[0] ?? null;
    if (droppedFile) {
      setFile(droppedFile);
      setError(null);
      setResults(null);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 relative overflow-hidden">
      {/* Starfield Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {stars.map(star => (
          <div
            key={star.id}
            className="absolute rounded-full bg-white animate-pulse"
            style={{
              left: `${star.left}%`,
              top: `${star.top}%`,
              width: `${star.size}px`,
              height: `${star.size}px`,
              opacity: star.opacity,
              animationDuration: '3s',
              animationDelay: `${star.animationDelay}s`
            }}
          />
        ))}
      </div>

      {/* Content */}
      <div className="relative z-10">
      {/* Header */}
      <header className="border-b border-white/10 bg-black/20 backdrop-blur-sm">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-3">
          <Search className="w-6 h-6 text-purple-400" />
          <h1 className="text-xl font-semibold text-white">ExoSense</h1>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-6 py-12">
        <div className="text-center mb-12">
          <h2 className="text-4xl font-bold text-white mb-4">
            Hunt for Exoplanets with AI
          </h2>
          <p className="text-lg text-slate-300">
            Upload light curve data to detect potential exoplanets using machine learning
          </p>
        </div>

        {/* Upload Section */}
        <div className="bg-white/5 backdrop-blur-md rounded-2xl border border-white/10 p-8 mb-8">
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            className="border-2 border-dashed border-purple-400/30 rounded-xl p-12 text-center hover:border-purple-400/50 transition-colors cursor-pointer bg-black/20"
          >
            <input
              type="file"
              id="file-upload"
              className="hidden"
              onChange={handleFileChange}
              accept=".csv,.fits,.txt"
            />
            <label
              htmlFor="file-upload"
              className="cursor-pointer"
              onClick={(e) => e.stopPropagation()}
            >
              <Upload className="w-16 h-16 text-purple-400 mx-auto mb-4" />
              <p className="text-xl text-white mb-2">
                {file ? file.name : 'Drop your data file here'}
              </p>
              <p className="text-slate-400">
                or click to browse (CSV, FITS, TXT)
              </p>
            </label>
          </div>

          {error && (
            <div className="mt-4 flex items-center gap-2 text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <p>{error}</p>
            </div>
          )}

          <button
            onClick={handleAnalyze}
            disabled={!file || loading}
            className="w-full mt-6 bg-purple-600 hover:bg-purple-700 disabled:bg-slate-700 disabled:cursor-not-allowed text-white font-semibold py-4 px-6 rounded-xl transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Analyzing...
              </>
            ) : (
              <>
                <Search className="w-5 h-5" />
                Analyze for Exoplanets
              </>
            )}
          </button>
        </div>

        {/* Results Section */}
        {results && (
          <div className="bg-white/5 backdrop-blur-md rounded-2xl border border-white/10 p-8 animate-fade-in">
            <div className="flex items-center gap-3 mb-6">
              {results.result.exoplanet_detected ? (
                <CheckCircle2 className="w-8 h-8 text-green-400" />
              ) : (
                <AlertCircle className="w-8 h-8 text-amber-400" />
              )}
              <h3 className="text-2xl font-bold text-white">
                {results.result.exoplanet_detected
                  ? 'Exoplanet Detected!'
                  : 'No Exoplanet Detected'}
              </h3>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-black/30 rounded-lg p-5 border border-white/5">
                <p className="text-slate-400 text-sm mb-1">Confidence</p>
                <p className="text-3xl font-bold text-white">{results.result.confidence.toFixed(1)}%</p>
              </div>

              <div className="bg-black/30 rounded-lg p-5 border border-white/5">
                <p className="text-slate-400 text-sm mb-1">Transit Depth</p>
                <p className="text-3xl font-bold text-white">{results.result.transit_depth?.toFixed(6) ?? '—'}</p>
              </div>

              <div className="bg-black/30 rounded-lg p-5 border border-white/5">
                <p className="text-slate-400 text-sm mb-1">Orbital Period</p>
                <p className="text-3xl font-bold text-white">{results.result.orbital_period?.toFixed(2) ?? '—'} days</p>
              </div>

              <div className="bg-black/30 rounded-lg p-5 border border-white/5">
                <p className="text-slate-400 text-sm mb-1">Data Source</p>
                <p className="text-xl font-semibold text-white">{file?.name}</p>
              </div>
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <div className="rounded-lg border border-white/10 bg-black/30 p-4">
                <h4 className="text-sm font-semibold text-white flex items-center gap-2">
                  <Clock className="h-4 w-4 text-purple-300" />
                  Processing Summary
                </h4>
                <p className="text-sm text-slate-300 mt-2">
                  Run ID: <span className="font-mono text-purple-200">{results.analysis_id.slice(0, 8)}</span>
                </p>
                <p className="text-sm text-slate-300">
                  Processing time: {results.processing_time.toFixed(2)} s
                </p>
              </div>

              <div className="rounded-lg border border-white/10 bg-black/30 p-4">
                <h4 className="text-sm font-semibold text-white">Key Metrics</h4>
                <ul className="mt-2 space-y-1 text-sm text-slate-300">
                  <li>
                    Signal-to-noise:{' '}
                    {typeof results.metrics?.snr === 'number' ? results.metrics.snr.toFixed(2) : '—'}
                  </li>
                  <li>Data points: {results.metrics?.data_points ?? '—'}</li>
                  <li>
                    Depth:{' '}
                    {typeof results.metrics?.depth === 'number' ? results.metrics.depth.toFixed(6) : '—'}
                  </li>
                </ul>
              </div>
            </div>

            {results.result.reasons.length > 0 && (
              <div className="mt-6 rounded-lg border border-white/10 bg-black/20 p-4">
                <h4 className="text-sm font-semibold text-white mb-2">Why we decided</h4>
                <ul className="list-disc pl-5 space-y-1 text-sm text-slate-300">
                  {results.result.reasons.map((reason: string) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
              </div>
            )}

            {results.sonification && (
              <SonificationPanel analysisId={results.analysis_id} series={results.sonification} />
            )}
          </div>
        )}

        {/* Info Section */}
        <div className="mt-12 bg-white/5 backdrop-blur-md rounded-2xl border border-white/10 p-8">
          <div className="flex items-start gap-3">
            <FileText className="w-6 h-6 text-purple-400 flex-shrink-0 mt-1" />
            <div>
              <h3 className="text-lg font-semibold text-white mb-2">About</h3>
              <p className="text-slate-300 leading-relaxed">
                This tool uses machine learning to analyze light curve data from space telescopes 
                like Kepler and TESS. Upload your astronomical data to detect the telltale dimming 
                patterns that indicate a planet passing in front of its host star.
              </p>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-white/10 bg-black/20 backdrop-blur-sm mt-16">
        <div className="max-w-5xl mx-auto px-6 py-6 text-center text-slate-400 text-sm">
          NASA Space Apps Challenge 2025 • Built with Next.js & FastAPI
        </div>
      </footer>
      </div>
    </div>
  );
}