import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
  CartesianGrid,
} from 'recharts';
import type { SignalMode } from '../hooks/useWebSocket';
import { openPrintWindow } from '../utils/reportPdf';

interface MetricsSnapshot {
  avg_wait_time: number;
  gini: number;
  avg_speed: number;
  active_agents: number;
  completed_agents: number;
}

interface ComparisonRow {
  city: string;
  intersections: number;
  webster: { episode_reward: number; mean_pressure: number; equity: number; gini: number };
  marl?: { episode_reward: number; mean_pressure: number; equity: number; gini: number };
  improvement_pct?: number;
}

interface TradeoffPoint {
  alpha: number;
  [cityKey: string]: number | string;
}

interface PolicyTogglePanelProps {
  mode: SignalMode;
  metrics: any;
  connected: boolean;
  simActive: boolean;
  onSwitch: (policy: 'webster' | 'rl') => void;
}

const CITY_COLORS = ['#3b82f6', '#ef4444', '#eab308', '#22c55e', '#a855f7', '#22d3ee'];

const CITY_LABELS: Record<string, string> = {
  toy: 'Toy (2x2)',
  chicago: 'Chicago',
  paris: 'Paris',
  ahmedabad: 'Ahmedabad',
  piedmont: 'Piedmont',
};

const ALPHAS = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1];

const LINE_CHART_MARGIN = { top: 4, right: 8, bottom: 0, left: -14 };

const isRlMode = (mode: SignalMode): boolean => mode === 'rl' || mode === 'ai';

function snapshotMetrics(m: any): MetricsSnapshot | null {
  if (!m) return null;
  return {
    avg_wait_time: m.avg_wait_time ?? 0,
    gini: m.gini_coefficient ?? 0,
    avg_speed: m.avg_speed ?? 0,
    active_agents: m.active_agents ?? 0,
    completed_agents: m.completed_agents ?? 0,
  };
}

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

export const PolicyTogglePanel: React.FC<PolicyTogglePanelProps> = ({
  mode,
  metrics,
  connected,
  simActive,
  onSwitch,
}) => {
  const [before, setBefore] = useState<MetricsSnapshot | null>(null);
  const [after, setAfter] = useState<MetricsSnapshot | null>(null);
  const [rows, setRows] = useState<ComparisonRow[] | null>(null);
  const metricsRef = useRef<any>(null);
  metricsRef.current = metrics;

  const rlActive = isRlMode(mode);

  // Toggle stores the metrics just before the switch ("before"), then samples
  // the running sim every 3 s while the learned policy is driving ("after").
  const handleSwitch = (policy: 'webster' | 'rl') => {
    setBefore(snapshotMetrics(metricsRef.current));
    setAfter(null);
    onSwitch(policy);
  };

  useEffect(() => {
    if (!before) return;
    const id = setInterval(() => {
      const s = snapshotMetrics(metricsRef.current);
      if (s) setAfter(s);
    }, 3000);
    return () => clearInterval(id);
  }, [before, simActive]);

  // A reset/stop clears the in-flight comparison so stale numbers never linger.
  useEffect(() => {
    if (!simActive) {
      setBefore(null);
      setAfter(null);
    }
  }, [simActive]);

  // Load the multi-city MARL-vs-Webster table and derive the alpha/beta
  // tradeoff curves (TR-ML-04: reward = alpha*pressure + (1-alpha)*equity).
  useEffect(() => {
    let cancelled = false;
    fetch('/comparison.json')
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then((data: ComparisonRow[]) => {
        if (cancelled) setRows(Array.isArray(data) ? data : null);
        else setRows(Array.isArray(data) ? data : null);
      })
      .catch(() => {
        if (!cancelled) setRows(null);
      });
    return () => { cancelled = true; };
  }, []);

  // Composite improvement % = alpha*pressure_imp% + (1-alpha)*equity_imp%,
  // both normalised to their own Webster baselines so the two objectives are
  // directly comparable. Reuses the measurements already in comparison.json.
  const tradeoff = useMemo<TradeoffPoint[]>(() => {
    if (!rows) return [];
    const valid = rows.filter((r) => r.marl && Math.abs(r.webster.mean_pressure) > 1e-9
      && Math.abs(r.webster.equity) > 1e-9);
    return ALPHAS.map((alpha) => {
      const point: TradeoffPoint = { alpha: Math.round(alpha * 100) / 100 };
      for (const r of valid) {
        const pressureImp = (r.marl!.mean_pressure - r.webster.mean_pressure)
          / Math.abs(r.webster.mean_pressure) * 100;
        const equityImp = (r.marl!.equity - r.webster.equity)
          / Math.abs(r.webster.equity) * 100;
        point[r.city] = Math.round((alpha * pressureImp + (1 - alpha) * equityImp) * 10) / 10;
      }
      return point;
    });
  }, [rows]);

  const modePill = (): { text: string; color: string; bg: string; border: string } => {
    if (!connected) return { text: 'Offline', color: '#9ca3af', bg: 'rgba(107,114,128,0.2)', border: '#4b5563' };
    if (rlActive) return { text: 'RL · learned control', color: '#c4b5fd', bg: 'rgba(139,92,246,0.2)', border: '#8b5cf6' };
    if (mode === 'webster') return { text: 'Webster · baseline', color: '#9ca3af', bg: 'rgba(107,114,128,0.2)', border: '#4b5563' };
    return { text: 'No signal data', color: '#9ca3af', bg: 'rgba(107,114,128,0.2)', border: '#4b5563' };
  };

  const toggleBtn = (active: boolean): React.CSSProperties => ({
    flex: '1 1 0',
    padding: '8px 0',
    border: active ? '1px solid #8b5cf6' : '1px solid #374151',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '12px',
    fontWeight: 600,
    fontFamily: 'system-ui, sans-serif',
    backgroundColor: active ? 'rgba(139, 92, 246, 0.25)' : 'transparent',
    color: active ? '#ffffff' : '#9ca3af',
    transition: 'all 0.2s',
  });

  const renderSnapshotRow = (
    label: string,
    beforeVal: number | undefined,
    afterVal: number | undefined,
    lowerBetter: boolean,
    format: (v: number) => string,
  ) => {
    const b = beforeVal ?? 0;
    const a = afterVal ?? 0;
    const hasAfter = after !== null && before !== null;
    const hasBefore = before !== null;
    const delta = hasAfter ? a - b : undefined;
    const improvement = delta !== undefined && delta !== 0
      ? lowerBetter ? -delta : delta
      : undefined;
    const pct = improvement !== undefined && b !== 0
      ? (improvement / Math.abs(b)) * 100 : undefined;
    const color = improvement === undefined
      ? '#9ca3af'
      : improvement > 0 ? '#4ade80' : '#f87171';
    const deltaText = delta !== undefined && delta !== 0
      ? `${improvement! > 0 ? '+' : ''}${format(improvement!)}${pct !== undefined ? ` (${improvement! > 0 ? '+' : ''}${pct.toFixed(1)}%)` : ''}`
      : '—';
    return (
      <tr key={label}>
        <td style={{ padding: '5px 8px', fontSize: '11px', color: '#9ca3af' }}>{label}</td>
        <td style={{ padding: '5px 8px', fontSize: '12px', textAlign: 'right', color: '#e5e7eb' }}>
          {hasBefore ? format(b) : '—'}
        </td>
        <td style={{ padding: '5px 8px', fontSize: '12px', textAlign: 'right', color: '#e5e7eb' }}>
          {hasAfter ? format(a) : '—'}
        </td>
        <td style={{ padding: '5px 8px', fontSize: '12px', textAlign: 'right', color }}>{deltaText}</td>
      </tr>
    );
  };

  const exportPdf = () => {
    const p = modePill();
    const fmt = (v: number) => v?.toFixed(2) ?? '—';
    const rowsHtml = (rows ?? []).map((r) => `
      <tr>
        <td>${CITY_LABELS[r.city] ?? r.city}</td>
        <td>${r.intersections}</td>
        <td>${fmt(r.webster.episode_reward)}</td>
        <td>${r.marl ? fmt(r.marl.episode_reward) : '—'}</td>
        <td>${r.improvement_pct !== undefined ? `${r.improvement_pct >= 0 ? '+' : ''}${r.improvement_pct.toFixed(1)}%` : '—'}</td>
      </tr>`).join('');

    const baHtml = before ? `
      <h2>2. Before / After (live)</h2>
      <table>
        <tr><th>Metric</th><th>Before</th><th>After</th></tr>
        <tr><td>Avg wait time (s)</td><td>${before.avg_wait_time.toFixed(1)}</td><td>${after ? after.avg_wait_time.toFixed(1) : '—'}</td></tr>
        <tr><td>Gini</td><td>${before.gini.toFixed(3)}</td><td>${after ? after.gini.toFixed(3) : '—'}</td></tr>
        <tr><td>Avg speed (km/h)</td><td>${(before.avg_speed * 3.6).toFixed(1)}</td><td>${after ? (after.avg_speed * 3.6).toFixed(1) : '—'}</td></tr>
        <tr><td>Active agents</td><td>${before.active_agents}</td><td>${after ? after.active_agents : '—'}</td></tr>
      </table>` : '';

    const tradeoffHtml = tradeoff.length > 0 ? `
      <h2>3. Trade-off curve (alpha/beta sweep)</h2>
      <p>Reward = alpha*pressure + (1&minus;alpha)*equity. Improvement % vs the Webster baseline, from ml/results/comparison.json.</p>
      <table>
        <tr><th>City</th><th>&alpha;=0 (equity)</th><th>&alpha;=0.5</th><th>&alpha;=1 (pressure)</th></tr>
        ${(rows ?? []).filter((r) => r.marl).map((r) => {
          const at = (a: number) => {
            const pt = tradeoff.find((t) => t.alpha === a);
            const v = pt ? pt[r.city] : undefined;
            return typeof v === 'number' ? `${v.toFixed(1)}%` : '—';
          };
          return `<tr><td>${CITY_LABELS[r.city] ?? r.city}</td><td>${at(0)}</td><td>${at(0.5)}</td><td>${at(1)}</td></tr>`;
        }).join('')}
      </table>` : '';

    const html = `<!doctype html><html><head><meta charset="utf-8">
      <title>NexusSim \u2014 Policy Comparison Report</title>
      <style>
        body { font-family: system-ui, -apple-system, sans-serif; color: #111827; padding: 32px; }
        h1 { font-size: 22px; margin: 0 0 4px; }
        .meta { color: #6b7280; font-size: 13px; margin-bottom: 24px; }
        h2 { font-size: 16px; margin: 24px 0 8px; border-bottom: 1px solid #e5e7eb; padding-bottom: 6px; }
        table { width: 100%; border-collapse: collapse; font-size: 13px; }
        th, td { border: 1px solid #e5e7eb; padding: 6px 10px; text-align: right; }
        th { background: #f3f4f6; }
        td:first-child, th:first-child { text-align: left; }
        .pill { display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 11px;
                border: 1px solid ${p.border}; color: ${p.color}; background: ${p.bg}; }
        @media print { body { padding: 0; } }
      </style></head><body>
      <h1>NexusSim — Policy Comparison Report</h1>
      <div class="meta">Generated ${new Date().toLocaleString()} &nbsp;·&nbsp;
        Mode: <span class="pill">${p.text}</span></div>
      <h2>1. MARL vs Webster (evaluation)</h2>
      <table>
        <tr><th>City</th><th>Intersections</th><th>Webster reward</th><th>MARL reward</th><th>Δ</th></tr>
        ${rowsHtml || '<tr><td colspan="5">No evaluation rows yet (train.evaluate has not been run).</td></tr>'}
      </table>
      ${baHtml}
      ${tradeoffHtml}
    </body></html>`;

    openPrintWindow(html);
  };

  const pill = modePill();

  return (
    <div style={panelStyle}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '12px' }}>
        <span style={{ backgroundColor: '#eab308', width: '8px', height: '24px', borderRadius: '4px', marginRight: '10px' }}></span>
        <h3 style={{ margin: 0, fontSize: '15px', fontWeight: 700 }}>Signal Policy Toggle</h3>
        <span style={{
          marginLeft: 'auto',
          fontSize: '10px',
          fontWeight: 700,
          letterSpacing: '1px',
          textTransform: 'uppercase',
          padding: '3px 8px',
          borderRadius: '9999px',
          color: pill.color,
          backgroundColor: pill.bg,
          border: `1px solid ${pill.border}`,
        }}>
          {pill.text}
        </span>
      </div>

      <div style={{ display: 'flex', gap: '6px', marginBottom: '12px' }}>
        <button
          onClick={() => handleSwitch('webster')}
          disabled={!connected || !simActive}
          style={{ ...toggleBtn(mode === 'webster'), opacity: !connected || !simActive ? 0.5 : 1 }}
          title={!simActive ? 'Start a simulation to toggle the signal policy' : 'Switch the whole network to fixed-cycle Webster timing'}
        >
          Webster Baseline
        </button>
        <button
          onClick={() => handleSwitch('rl')}
          disabled={!connected || !simActive}
          style={{ ...toggleBtn(rlActive), opacity: !connected || !simActive ? 0.5 : 1 }}
          title={!simActive ? 'Start a simulation to toggle the signal policy' : 'Switch the whole network to the learned RL policy'}
        >
          RL (AI) Control
        </button>
      </div>

      {!simActive && (
        <div style={{ fontSize: '11px', color: '#6b7280', marginBottom: '10px' }}>
          Start a simulation to toggle the signal policy.
        </div>
      )}

      <div style={{ maxHeight: '300px', overflowY: 'auto' }}>
        <div style={labelStyle}>Before / After</div>
        {!before ? (
          <div style={{ fontSize: '12px', color: '#9ca3af' }}>
            Toggle the policy to capture a before/after comparison. The difference is sampled every 3 s.
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', padding: '5px 8px', fontSize: '10px', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Metric</th>
                <th style={{ textAlign: 'right', padding: '5px 8px', fontSize: '10px', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Before</th>
                <th style={{ textAlign: 'right', padding: '5px 8px', fontSize: '10px', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.5px' }}>After</th>
                <th style={{ textAlign: 'right', padding: '5px 8px', fontSize: '10px', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Δ</th>
              </tr>
            </thead>
            <tbody>
              {renderSnapshotRow('Avg Wait', before.avg_wait_time, after?.avg_wait_time, true, (v) => `${v.toFixed(1)}s`)}
              {renderSnapshotRow('Gini', before.gini, after?.gini, true, (v) => v.toFixed(3))}
              {renderSnapshotRow('Avg Speed', before.avg_speed * 3.6, after ? after.avg_speed * 3.6 : undefined, false, (v) => `${v.toFixed(1)} km/h`)}
              {renderSnapshotRow('Active', before.active_agents, after?.active_agents, true, (v) => String(Math.round(v)))}
              {renderSnapshotRow('Completed', before.completed_agents, after?.completed_agents, false, (v) => String(Math.round(v)))}
            </tbody>
          </table>
        )}
        {before && (
          <button
            onClick={() => { setBefore(null); setAfter(null); }}
            style={{
              marginTop: '8px',
              padding: '5px 10px',
              border: '1px solid #374151',
              borderRadius: '6px',
              cursor: 'pointer',
              fontSize: '11px',
              fontWeight: 600,
              fontFamily: 'system-ui, sans-serif',
              backgroundColor: 'transparent',
              color: '#9ca3af',
            }}
          >
            Reset comparison
          </button>
        )}

        <div style={{ ...labelStyle, marginTop: '14px' }}>Trade-off curve (α/β sweep)</div>
        {tradeoff.length === 0 ? (
          <div style={{ fontSize: '12px', color: '#9ca3af' }}>
            No evaluation data yet — run <code>train.evaluate</code> to populate <code>ml/results/comparison.json</code>.
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={180}>
            <LineChart data={tradeoff} margin={LINE_CHART_MARGIN}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(107,114,128,0.2)" />
              <XAxis
                dataKey="alpha"
                tick={{ fill: '#9ca3af', fontSize: 10 }}
                axisLine={false}
                tickLine={false}
                tickFormatter={(a) => `α ${Number(a).toFixed(1)}`}
                label={{ value: 'α (pressure weight)', position: 'insideBottom', offset: -2, fill: '#6b7280', fontSize: 10 }}
              />
              <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '6px', fontSize: '12px' }}
                labelStyle={{ color: '#ffffff' }}
                formatter={(value: any, name: any) => [`${Number(value).toFixed(1)}%`, CITY_LABELS[String(name)] ?? String(name)]}
                labelFormatter={(label) => `α = ${Number(label).toFixed(1)}, β = ${(1 - Number(label)).toFixed(1)}`}
              />
              <Legend wrapperStyle={{ fontSize: '11px', color: '#9ca3af' }} />
              {(rows ?? []).filter((r) => r.marl).map((r, i) => (
                <Line
                  key={r.city}
                  type="monotone"
                  dataKey={r.city}
                  stroke={CITY_COLORS[i % CITY_COLORS.length]}
                  strokeWidth={2}
                  dot={false}
                  isAnimationActive={false}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
        <div style={{ fontSize: '10px', color: '#6b7280', marginTop: '6px' }}>
          Reward = α·pressure + (1−α)·equity; α sweeps pressure weight. Values are improvement % vs Webster from {rows?.length ?? 0} evaluated cities.
        </div>

        <button
          onClick={exportPdf}
          disabled={!before && (rows?.length ?? 0) === 0}
          style={{
            marginTop: '12px',
            width: '100%',
            padding: '8px 0',
            border: '1px solid #374151',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '12px',
            fontWeight: 600,
            fontFamily: 'system-ui, sans-serif',
            backgroundColor: 'rgba(59, 130, 246, 0.15)',
            color: '#e5e7eb',
            opacity: !before && (rows?.length ?? 0) === 0 ? 0.5 : 1,
          }}
          title="Open a print-ready report (choose Save as PDF in the dialog)"
        >
          Export PDF report
        </button>
      </div>
    </div>
  );
};

export default PolicyTogglePanel;