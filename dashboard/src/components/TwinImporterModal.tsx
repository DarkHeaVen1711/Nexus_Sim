import React, { useState, useEffect, useRef } from 'react';
import { ENDPOINTS } from '../config/api';

interface TwinImporterModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCitySelected: (cityId: string) => void;
}

interface IngestionJobProgress {
  job_id: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  stage: string;
  progress_pct: number;
  message: string;
  elapsed_seconds: number;
  metrics: {
    nodes?: number;
    edges?: number;
    zones?: number;
    elapsed_s?: number;
  };
  error?: string | null;
  result?: {
    city_id: string;
    city_name: string;
    node_count: number;
    edge_count: number;
  };
}

const PRESET_LOCATIONS = [
  'Shantigram, Ahmedabad',
  'Manhattan Midtown, New York',
  'Paris 8e, France',
  'Piedmont, California',
  'Connaught Place, New Delhi',
];

export const TwinImporterModal: React.FC<TwinImporterModalProps> = ({
  isOpen,
  onClose,
  onCitySelected,
}) => {
  const [activeTab, setActiveTab] = useState<'search' | 'upload'>('search');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [cityName, setCityName] = useState('');
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [progress, setProgress] = useState<IngestionJobProgress | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const pollIntervalRef = useRef<number | null>(null);

  // Clear polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  // Poll progress when activeJobId changes
  useEffect(() => {
    if (!activeJobId) return;

    const poll = async () => {
      try {
        const resp = await fetch(`${ENDPOINTS.GATEWAY_URL}/api/v1/twin/progress/${activeJobId}`);
        if (!resp.ok) return;
        const data: IngestionJobProgress = await resp.json();
        setProgress(data);

        if (data.status === 'completed' || data.status === 'failed') {
          if (pollIntervalRef.current) {
            clearInterval(pollIntervalRef.current);
            pollIntervalRef.current = null;
          }
          setIsSubmitting(false);
        }
      } catch (err: any) {
        console.error('Error polling twin ingestion progress:', err);
      }
    };

    poll();
    pollIntervalRef.current = window.setInterval(poll, 600);

    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, [activeJobId]);

  if (!isOpen) return null;

  const handleStartSearch = async () => {
    if (!searchQuery.trim()) return;
    setIsSubmitting(true);
    setErrorMessage(null);
    setProgress(null);

    try {
      const resp = await fetch(`${ENDPOINTS.GATEWAY_URL}/api/v1/twin/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery.trim(), workspace_id: 'default' }),
      });

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || 'Failed to initiate search ingestion');
      }

      const data = await resp.json();
      setActiveJobId(data.job_id);
    } catch (err: any) {
      setIsSubmitting(false);
      setErrorMessage(err.message || 'An unexpected error occurred');
    }
  };

  const handleStartUpload = async () => {
    if (!selectedFile) return;
    setIsSubmitting(true);
    setErrorMessage(null);
    setProgress(null);

    const formData = new FormData();
    formData.append('file', selectedFile);
    if (cityName.trim()) {
      formData.append('city_name', cityName.trim());
    }

    try {
      const resp = await fetch(`${ENDPOINTS.GATEWAY_URL}/api/v1/twin/upload`, {
        method: 'POST',
        body: formData,
      });

      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || 'Failed to upload OSM file');
      }

      const data = await resp.json();
      setActiveJobId(data.job_id);
    } catch (err: any) {
      setIsSubmitting(false);
      setErrorMessage(err.message || 'An unexpected error occurred during upload');
    }
  };

  const handleLaunch = () => {
    if (progress?.result?.city_id) {
      onCitySelected(progress.result.city_id);
      onClose();
    }
  };

  const handleReset = () => {
    setActiveJobId(null);
    setProgress(null);
    setIsSubmitting(false);
    setErrorMessage(null);
  };

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.75)',
        backdropFilter: 'blur(6px)',
        zIndex: 2000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}
    >
      <div
        style={{
          width: '560px',
          maxWidth: '92vw',
          backgroundColor: '#111827',
          border: '1px solid #374151',
          borderRadius: '14px',
          boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.5)',
          color: '#f9fafb',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '16px 20px',
            borderBottom: '1px solid #1f2937',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            background: 'linear-gradient(180deg, #1f2937 0%, #111827 100%)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '28px',
                height: '28px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontWeight: 700,
                fontSize: '14px',
              }}
            >
              🌐
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '15px', letterSpacing: '-0.2px' }}>
                NexusTwin Ingestion Engine
              </div>
              <div style={{ fontSize: '12px', color: '#9ca3af' }}>
                Instant Digital Twin Auto-Synthesis & OSM Ingestion
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={isSubmitting}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#9ca3af',
              fontSize: '20px',
              cursor: isSubmitting ? 'not-allowed' : 'pointer',
              padding: '4px',
            }}
          >
            ✕
          </button>
        </div>

        {/* Tab Navigation (Disabled during active ingestion) */}
        {!activeJobId && (
          <div
            style={{
              display: 'flex',
              borderBottom: '1px solid #1f2937',
              backgroundColor: '#0f172a',
            }}
          >
            <button
              onClick={() => setActiveTab('search')}
              style={{
                flex: 1,
                padding: '12px',
                background: activeTab === 'search' ? '#111827' : 'transparent',
                border: 'none',
                borderBottom: activeTab === 'search' ? '2px solid #3b82f6' : '2px solid transparent',
                color: activeTab === 'search' ? '#ffffff' : '#9ca3af',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
              }}
            >
              <span>🔍</span> Stage 2: Global Search Auto-Synthesis
            </button>
            <button
              onClick={() => setActiveTab('upload')}
              style={{
                flex: 1,
                padding: '12px',
                background: activeTab === 'upload' ? '#111827' : 'transparent',
                border: 'none',
                borderBottom: activeTab === 'upload' ? '2px solid #3b82f6' : '2px solid transparent',
                color: activeTab === 'upload' ? '#ffffff' : '#9ca3af',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
              }}
            >
              <span>📁</span> Stage 1: File Drop Ingestion
            </button>
          </div>
        )}

        {/* Modal Body */}
        <div style={{ padding: '20px' }}>
          {errorMessage && (
            <div
              style={{
                backgroundColor: 'rgba(239, 68, 68, 0.15)',
                border: '1px solid #ef4444',
                color: '#fca5a5',
                padding: '10px 14px',
                borderRadius: '8px',
                fontSize: '13px',
                marginBottom: '16px',
              }}
            >
              {errorMessage}
            </div>
          )}

          {/* Active Job Progress View */}
          {activeJobId ? (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', alignItems: 'center' }}>
                <span
                  style={{
                    fontSize: '11px',
                    fontWeight: 700,
                    textTransform: 'uppercase',
                    color: '#60a5fa',
                    letterSpacing: '0.5px',
                  }}
                >
                  {progress?.stage || 'PROCESSING'}
                </span>
                <span style={{ fontSize: '13px', fontWeight: 700, color: '#f3f4f6' }}>
                  {progress?.progress_pct ?? 0}%
                </span>
              </div>

              {/* Progress Track */}
              <div
                style={{
                  width: '100%',
                  height: '8px',
                  backgroundColor: '#1f2937',
                  borderRadius: '999px',
                  overflow: 'hidden',
                  marginBottom: '14px',
                }}
              >
                <div
                  style={{
                    width: `${progress?.progress_pct ?? 5}%`,
                    height: '100%',
                    background:
                      progress?.status === 'failed'
                        ? '#ef4444'
                        : 'linear-gradient(90deg, #3b82f6 0%, #10b981 100%)',
                    transition: 'width 0.4s ease',
                  }}
                />
              </div>

              {/* Status Message */}
              <div
                style={{
                  fontSize: '13px',
                  color: '#9ca3af',
                  marginBottom: '16px',
                  minHeight: '20px',
                }}
              >
                {progress?.message || 'Executing topology pipeline...'}
              </div>

              {/* Metrics Grid */}
              {progress?.metrics && Object.keys(progress.metrics).length > 0 && (
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(3, 1fr)',
                    gap: '10px',
                    marginBottom: '20px',
                  }}
                >
                  {progress.metrics.nodes !== undefined && (
                    <div style={{ backgroundColor: '#1e293b', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
                      <div style={{ fontSize: '11px', color: '#94a3b8' }}>Nodes Cleaned</div>
                      <div style={{ fontSize: '16px', fontWeight: 700, color: '#38bdf8' }}>
                        {progress.metrics.nodes.toLocaleString()}
                      </div>
                    </div>
                  )}
                  {progress.metrics.edges !== undefined && (
                    <div style={{ backgroundColor: '#1e293b', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
                      <div style={{ fontSize: '11px', color: '#94a3b8' }}>Edges & Lanes</div>
                      <div style={{ fontSize: '16px', fontWeight: 700, color: '#34d399' }}>
                        {progress.metrics.edges.toLocaleString()}
                      </div>
                    </div>
                  )}
                  {progress.metrics.elapsed_s !== undefined && (
                    <div style={{ backgroundColor: '#1e293b', padding: '10px', borderRadius: '8px', textAlign: 'center' }}>
                      <div style={{ fontSize: '11px', color: '#94a3b8' }}>Total Duration</div>
                      <div style={{ fontSize: '16px', fontWeight: 700, color: '#fbbf24' }}>
                        {progress.metrics.elapsed_s}s
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Action Buttons */}
              <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
                {progress?.status === 'completed' ? (
                  <button
                    onClick={handleLaunch}
                    style={{
                      backgroundColor: '#10b981',
                      color: '#ffffff',
                      border: 'none',
                      padding: '10px 18px',
                      borderRadius: '8px',
                      fontWeight: 700,
                      cursor: 'pointer',
                      fontSize: '13px',
                      boxShadow: '0 4px 12px rgba(16, 185, 129, 0.4)',
                    }}
                  >
                    🚀 Launch Simulation in Digital Twin
                  </button>
                ) : progress?.status === 'failed' ? (
                  <button
                    onClick={handleReset}
                    style={{
                      backgroundColor: '#374151',
                      color: '#ffffff',
                      border: 'none',
                      padding: '8px 16px',
                      borderRadius: '8px',
                      fontWeight: 600,
                      cursor: 'pointer',
                      fontSize: '13px',
                    }}
                  >
                    Try Again
                  </button>
                ) : (
                  <span style={{ fontSize: '12px', color: '#6b7280', alignSelf: 'center' }}>
                    Elapsed: {progress?.elapsed_seconds ?? 0}s (Sub-20s target)
                  </span>
                )}
              </div>
            </div>
          ) : activeTab === 'search' ? (
            /* Search Tab */
            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: '#d1d5db', display: 'block', marginBottom: '8px' }}>
                Search Global Location or Neighborhood:
              </label>
              <div style={{ display: 'flex', gap: '8px', marginBottom: '14px' }}>
                <input
                  type="text"
                  placeholder="e.g. Shantigram, Ahmedabad | Times Square, NY"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleStartSearch()}
                  style={{
                    flex: 1,
                    backgroundColor: '#1f2937',
                    border: '1px solid #374151',
                    borderRadius: '8px',
                    color: '#ffffff',
                    padding: '10px 12px',
                    fontSize: '13px',
                    outline: 'none',
                  }}
                />
                <button
                  onClick={handleStartSearch}
                  disabled={!searchQuery.trim() || isSubmitting}
                  style={{
                    backgroundColor: '#3b82f6',
                    color: '#ffffff',
                    border: 'none',
                    borderRadius: '8px',
                    padding: '10px 16px',
                    fontWeight: 600,
                    fontSize: '13px',
                    cursor: searchQuery.trim() && !isSubmitting ? 'pointer' : 'not-allowed',
                    opacity: searchQuery.trim() && !isSubmitting ? 1 : 0.6,
                  }}
                >
                  Synthesize
                </button>
              </div>

              {/* Preset location chips */}
              <div style={{ marginBottom: '12px' }}>
                <div style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '6px' }}>
                  Quick Presets:
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
                  {PRESET_LOCATIONS.map((loc) => (
                    <button
                      key={loc}
                      onClick={() => setSearchQuery(loc)}
                      style={{
                        backgroundColor: '#1f2937',
                        border: '1px solid #374151',
                        borderRadius: '6px',
                        color: '#93c5fd',
                        fontSize: '11px',
                        padding: '4px 8px',
                        cursor: 'pointer',
                      }}
                    >
                      {loc}
                    </button>
                  ))}
                </div>
              </div>

              <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '10px', lineHeight: 1.5 }}>
                💡 <b>How it works:</b> Queries OpenStreetMap Overpass API for road geometries, synthesizes lane
                hierarchies and traffic signals, generates synthetic gravity OD matrices, and prepares the C++ engine in ≤ 20 seconds.
              </div>
            </div>
          ) : (
            /* Upload Tab */
            <div>
              <label style={{ fontSize: '12px', fontWeight: 600, color: '#d1d5db', display: 'block', marginBottom: '8px' }}>
                Upload OpenStreetMap File (.osm, .osm.pbf, .graphml):
              </label>

              <div
                style={{
                  border: '2px dashed #374151',
                  borderRadius: '10px',
                  padding: '24px',
                  textAlign: 'center',
                  backgroundColor: '#1f2937',
                  cursor: 'pointer',
                  marginBottom: '14px',
                }}
                onClick={() => document.getElementById('twin-file-input')?.click()}
              >
                <input
                  id="twin-file-input"
                  type="file"
                  accept=".osm,.pbf,.graphml,.xml"
                  style={{ display: 'none' }}
                  onChange={(e) => {
                    if (e.target.files?.[0]) {
                      setSelectedFile(e.target.files[0]);
                      if (!cityName) {
                        const nameWithoutExt = e.target.files[0].name.replace(/\.[^/.]+$/, '');
                        setCityName(nameWithoutExt.replace(/[-_]/g, ' ').replace(/\b\w/g, l => l.toUpperCase()));
                      }
                    }
                  }}
                />
                <div style={{ fontSize: '28px', marginBottom: '6px' }}>📂</div>
                <div style={{ fontSize: '13px', fontWeight: 600, color: '#e5e7eb' }}>
                  {selectedFile ? selectedFile.name : 'Click or drag file to upload'}
                </div>
                <div style={{ fontSize: '11px', color: '#9ca3af', marginTop: '4px' }}>
                  {selectedFile ? `${(selectedFile.size / (1024 * 1024)).toFixed(2)} MB` : 'Up to 500 MB (.osm, .osm.pbf, .graphml)'}
                </div>
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label style={{ fontSize: '11px', color: '#9ca3af', display: 'block', marginBottom: '4px' }}>
                  City Display Name:
                </label>
                <input
                  type="text"
                  placeholder="e.g. Mumbai Downtown"
                  value={cityName}
                  onChange={(e) => setCityName(e.target.value)}
                  style={{
                    width: '100%',
                    backgroundColor: '#1f2937',
                    border: '1px solid #374151',
                    borderRadius: '8px',
                    color: '#ffffff',
                    padding: '8px 12px',
                    fontSize: '13px',
                    outline: 'none',
                    boxSizing: 'border-box',
                  }}
                />
              </div>

              <button
                onClick={handleStartUpload}
                disabled={!selectedFile || isSubmitting}
                style={{
                  width: '100%',
                  backgroundColor: '#10b981',
                  color: '#ffffff',
                  border: 'none',
                  borderRadius: '8px',
                  padding: '10px 0',
                  fontWeight: 600,
                  fontSize: '13px',
                  cursor: selectedFile && !isSubmitting ? 'pointer' : 'not-allowed',
                  opacity: selectedFile && !isSubmitting ? 1 : 0.6,
                }}
              >
                Ingest & Process File
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
