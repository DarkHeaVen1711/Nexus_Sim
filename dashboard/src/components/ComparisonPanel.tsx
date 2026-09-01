import React, { useEffect, useState } from 'react';

interface EvalMetrics {
  episode_reward: number;
  mean_pressure: number;
  equity: number;
  gini: number;
}

interface CityComparison {
  city: string;
  intersections: number;
  webster: EvalMetrics;
  marl?: EvalMetrics;
  improvement_pct?: number;
}

const CITY_LABELS: Record<string, string> = {
  toy: 'Toy (2x2)',
  chicago: 'Chicago',
  paris: 'Paris',
  ahmedabad: 'Ahmedabad',
  piedmont: 'Piedmont',
};

function cityLabel(id: string): string {
  return CITY_LABELS[id] ?? id;
}

function metricCell(key: keyof EvalMetrics, v?: EvalMetrics): string {
  if (!v) return '—';
  const val = v[key];
  if (key === 'gini') return val.toFixed(3);
  return val.toFixed(1);
}

export const ComparisonPanel: React.FC = () => {
  const [rows, setRows] = useState<CityComparison[] | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch('/comparison.json')
      .then(r => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: CityComparison[]) => {
        if (cancelled) return;
        setRows(Array.isArray(data) ? data : null);
      })
      .catch((e) => {
        console.error('Failed to load comparison results', e);
        if (!cancelled) setError(true);
      });
    return () => { cancelled = true; };
  }, []);

  const panelStyle: React.CSSProperties = {
    position: 'absolute',
    bottom: '20px',
    right: '20px',
    zIndex: 1000,
    backgroundColor: 'rgba(17, 24, 39, 0.92)',
    backdropFilter: 'blur(8px)',
    color: '#ffffff',
    padding: '20px',
    borderRadius: '12px',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
    border: '1px solid #374151',
    maxWidth: '420px',
    fontFamily: 'system-ui, sans-serif',
  };

  const labelStyle: React.CSSProperties = {
    color: '#9ca3af', fontSize: '11px', fontWeight: 600,
    textTransform: 'uppercase' as const, letterSpacing: '1px', marginBottom: '10px',
  };

  const thStyle: React.CSSProperties = {
    textAlign: 'left', padding: '6px 8px', fontSize: '11px',
    color: '#9ca3af', textTransform: 'uppercase' as const, letterSpacing: '0.5px',
  };
  const tdStyle: React.CSSProperties = { padding: '6px 8px', fontSize: '12px', borderTop: '1px solid rgba(107, 114, 128, 0.2)' };

  const improvementColor = (p?: number): string => {
    if (p === undefined) return '#9ca3af';
    return p >= 0 ? '#4ade80' : '#f87171';
  };

  return (
    <div style={panelStyle}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '12px' }}>
        <span style={{ backgroundColor: '#8b5cf6', width: '8px', height: '24px', borderRadius: '4px', marginRight: '10px' }}></span>
        <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700 }}>MARL vs Webster Baseline</h3>
      </div>

      {error && (
        <div style={{ fontSize: '13px', color: '#f87171' }}>
          Comparison results unavailable (no evaluation output yet).
        </div>
      )}

      {!error && rows === null && (
        <div style={{ fontSize: '13px', color: '#9ca3af' }}>Loading comparison results…</div>
      )}

      {!error && rows && rows.length > 0 && (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th style={thStyle}>City</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Intersections</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Webster</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>MARL</th>
              <th style={{ ...thStyle, textAlign: 'right' }}>Δ Reward</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(row => (
              <tr key={row.city}>
                <td style={tdStyle}>{cityLabel(row.city)}</td>
                <td style={{ ...tdStyle, textAlign: 'right', color: '#9ca3af' }}>{row.intersections}</td>
                <td style={{ ...tdStyle, textAlign: 'right', color: '#9ca3af' }}>
                  {metricCell('episode_reward', row.webster)}
                </td>
                <td style={{ ...tdStyle, textAlign: 'right', color: row.marl ? '#c4b5fd' : '#9ca3af' }}>
                  {metricCell('episode_reward', row.marl)}
                </td>
                <td style={{ ...tdStyle, textAlign: 'right', color: improvementColor(row.improvement_pct) }}>
                  {row.improvement_pct !== undefined ? `${row.improvement_pct >= 0 ? '+' : ''}${row.improvement_pct.toFixed(1)}%` : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {!error && rows && rows.length === 0 && (
        <div style={{ fontSize: '13px', color: '#9ca3af' }}>No comparison rows yet.</div>
      )}

      <div style={{ ...labelStyle, marginTop: '12px' }}>
        Reward (lower magnitude = less wait); Δ % relative to Webster
      </div>
    </div>
  );
};

