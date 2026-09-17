import React, { useState } from 'react';
import type { IntersectionSignalState, SignalMode } from '../hooks/useWebSocket';

interface PolicyComparisonPanelProps {
  signals: IntersectionSignalState[];
  engineMode: SignalMode;
  connected: boolean;
  simActive: boolean;
  onSwitchPolicy: (policy: 'webster' | 'rl' | 'fuzzy', intersectionId?: number | null) => void;
}

export const PolicyComparisonPanel: React.FC<PolicyComparisonPanelProps> = ({
  signals,
  engineMode,
  connected,
  simActive,
  onSwitchPolicy,
}) => {
  const [selectedIntersection, setSelectedIntersection] = useState<number | null>(null);

  const panelStyle: React.CSSProperties = {
    color: '#ffffff',
    padding: 0,
    fontFamily: 'system-ui, sans-serif',
    borderTop: '1px solid rgba(107, 114, 128, 0.2)',
    marginTop: '12px',
    paddingTop: '12px',
  };

  const labelStyle: React.CSSProperties = {
    color: '#9ca3af',
    fontSize: '11px',
    fontWeight: 600,
    textTransform: 'uppercase',
    letterSpacing: '1px',
    marginBottom: '10px',
  };

  const selectStyle: React.CSSProperties = {
    width: '100%',
    padding: '6px 10px',
    backgroundColor: '#1f2937',
    color: '#ffffff',
    border: '1px solid #374151',
    borderRadius: '6px',
    fontSize: '12px',
    marginBottom: '8px',
  };

  const btnStyle = (active: boolean): React.CSSProperties => ({
    flex: '1 1 0',
    padding: '6px 0',
    border: active ? '1px solid #8b5cf6' : '1px solid #374151',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: 600,
    backgroundColor: active ? 'rgba(139, 92, 246, 0.25)' : 'transparent',
    color: active ? '#ffffff' : '#9ca3af',
    transition: 'all 0.2s',
  });

  return (
    <div style={panelStyle}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '12px' }}>
        <span style={{ backgroundColor: '#a855f7', width: '8px', height: '24px', borderRadius: '4px', marginRight: '10px' }}></span>
        <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700 }}>Intersection Signal Control</h3>
      </div>

      <div style={labelStyle}>Per-Intersection Override</div>

      {signals.length === 0 ? (
        <div style={{ fontSize: '12px', color: '#9ca3af' }}>
          {simActive ? 'No signalized intersections loaded.' : 'Start a simulation to manage intersections.'}
        </div>
      ) : (
        <>
          <select
            value={selectedIntersection ?? ''}
            onChange={(e) => setSelectedIntersection(e.target.value ? Number(e.target.value) : null)}
            style={selectStyle}
          >
            <option value="">Select an Intersection ({signals.length} active)</option>
            {signals.map((sig) => (
              <option key={sig.id} value={sig.id}>
                Intersection #{sig.id} — [{sig.mode.toUpperCase()}] Phase {sig.phase}
              </option>
            ))}
          </select>

          {selectedIntersection !== null && (
            <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
              <button
                disabled={!connected || !simActive}
                onClick={() => onSwitchPolicy('webster', selectedIntersection)}
                style={btnStyle(signals.find((s) => s.id === selectedIntersection)?.mode === 'webster')}
              >
                Webster
              </button>
              <button
                disabled={!connected || !simActive}
                onClick={() => onSwitchPolicy('fuzzy', selectedIntersection)}
                style={btnStyle(signals.find((s) => s.id === selectedIntersection)?.mode === 'fuzzy')}
              >
                Fuzzy
              </button>
              <button
                disabled={!connected || !simActive}
                onClick={() => onSwitchPolicy('rl', selectedIntersection)}
                style={btnStyle(signals.find((s) => s.id === selectedIntersection)?.mode === 'rl')}
              >
                RL (AI)
              </button>
            </div>
          )}
        </>
      )}

      <div style={{ ...labelStyle, marginTop: '14px' }}>Network Policy</div>
      <div style={{ fontSize: '12px', color: '#9ca3af' }}>
        Current network baseline: <span style={{ color: '#ffffff', fontWeight: 600 }}>{engineMode ?? 'webster'}</span>
      </div>
    </div>
  );
};

export default PolicyComparisonPanel;
