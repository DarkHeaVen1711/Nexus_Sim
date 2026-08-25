import React, { useMemo } from 'react';
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { giniLabel, giniColor } from '../constants';

interface ZoneMetric {
  zone_id: number;
  wait_time: number;
}

interface MetricsPanelProps {
  metrics: {
    avg_speed?: number;
    active_agents?: number;
    completed_agents?: number;
    avg_wait_time?: number;
    gini_coefficient?: number;
  } | null;
  zoneMetrics?: ZoneMetric[];
  signalMode?: 'ai' | 'webster' | null;
}

function barColor(wt: number, maxWt: number): string {
  if (maxWt <= 0) return '#22c55e';
  const t = wt / maxWt;
  if (t < 0.33) return '#22c55e';
  if (t < 0.66) return '#eab308';
  return '#ef4444';
}

export const MetricsPanel: React.FC<MetricsPanelProps> = ({ metrics, zoneMetrics, signalMode }) => {
  if (!metrics) return null;

  const gini = metrics.gini_coefficient ?? 0;
  const waitTime = metrics.avg_wait_time ?? 0;

  const topZones = useMemo(() => {
    if (!zoneMetrics || zoneMetrics.length === 0) return [];
    const sorted = [...zoneMetrics].sort((a, b) => b.wait_time - a.wait_time);
    return sorted.slice(0, 5);
  }, [zoneMetrics]);

  const maxBarWt = useMemo(() => {
    if (topZones.length === 0) return 1;
    return Math.max(...topZones.map(z => z.wait_time), 0.1);
  }, [topZones]);

  const panelStyle: React.CSSProperties = {
    position: 'absolute',
    top: '20px',
    right: '20px',
    zIndex: 1000,
    backgroundColor: 'rgba(17, 24, 39, 0.9)',
    backdropFilter: 'blur(8px)',
    color: '#ffffff',
    padding: '24px',
    borderRadius: '12px',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
    border: '1px solid #374151',
    width: '300px',
    fontFamily: 'system-ui, sans-serif'
  };

  const divider = <div style={{ height: '1px', backgroundColor: 'rgba(55, 65, 81, 0.5)', width: '100%' }} />;
  const labelStyle: React.CSSProperties = { color: '#9ca3af', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase' as const, letterSpacing: '1px', marginBottom: '4px' };
  const valueStyle: React.CSSProperties = { fontSize: '28px', fontWeight: 300 };

  return (
    <div style={panelStyle}>
      <h2 style={{ fontSize: '18px', fontWeight: 'bold', margin: '0 0 20px 0', display: 'flex', alignItems: 'center' }}>
        <span style={{ backgroundColor: '#3b82f6', width: '8px', height: '24px', borderRadius: '4px', marginRight: '12px' }}></span>
        Simulation Metrics
        {signalMode && (
          <span style={{
            marginLeft: 'auto',
            fontSize: '10px',
            fontWeight: 700,
            letterSpacing: '1px',
            textTransform: 'uppercase' as const,
            padding: '3px 8px',
            borderRadius: '9999px',
            color: signalMode === 'ai' ? '#c4b5fd' : '#9ca3af',
            backgroundColor: signalMode === 'ai' ? 'rgba(139, 92, 246, 0.2)' : 'rgba(107, 114, 128, 0.2)',
            border: `1px solid ${signalMode === 'ai' ? '#8b5cf6' : '#4b5563'}`,
          }}>
            {signalMode === 'ai' ? 'AI Mode' : 'Baseline'}
          </span>
        )}
      </h2>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div>
          <div style={labelStyle}>Avg Speed</div>
          <div style={valueStyle}>
            {((metrics.avg_speed ?? 0) * 3.6).toFixed(1)} <span style={{ fontSize: '13px', color: '#6b7280' }}>km/h</span>
          </div>
          <div style={{ fontSize: '13px', color: '#9ca3af', marginTop: '2px' }}>
            {((metrics.avg_speed ?? 0) * 2.236936).toFixed(1)} mph
          </div>
        </div>

        {divider}

        <div>
          <div style={labelStyle}>Active Agents</div>
          <div style={{ ...valueStyle, color: '#4ade80' }}>{metrics.active_agents ?? 0}</div>
        </div>

        {divider}

        <div>
          <div style={labelStyle}>Completed</div>
          <div style={{ ...valueStyle, color: '#3b82f6' }}>{metrics.completed_agents ?? 0}</div>
        </div>

        {divider}

        <div>
          <div style={labelStyle}>Avg Wait Time</div>
          <div style={{ ...valueStyle, color: '#f59e0b' }}>
            {waitTime.toFixed(1)} <span style={{ fontSize: '13px', color: '#6b7280' }}>s</span>
          </div>
        </div>

        {divider}

        <div>
          <div style={labelStyle}>Gini Coefficient</div>
          <div style={{ ...valueStyle, color: giniColor(gini) }}>
            {gini.toFixed(3)}
          </div>
          <div style={{ fontSize: '12px', color: giniColor(gini), marginTop: '2px' }}>
            {giniLabel(gini)}
          </div>
        </div>

        {topZones.length > 0 && <>{divider}</>}

        {topZones.length > 0 && (
          <div>
            <div style={labelStyle}>Top Congested Zones</div>
            <div style={{ marginTop: '8px' }}>
              <ResponsiveContainer width="100%" height={150}>
                <BarChart data={topZones} margin={{ top: 4, right: 4, bottom: 0, left: -20 }}>
                  <XAxis dataKey="zone_id" tick={{ fill: '#9ca3af', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#9ca3af', fontSize: 10 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '6px', fontSize: '12px' }}
                    labelStyle={{ color: '#ffffff' }}
                    formatter={(value) => [`${Number(value).toFixed(1)}s`, 'Wait Time']}
                    labelFormatter={(label) => `Zone ${String(label)}`}
                  />
                  <Bar dataKey="wait_time" radius={[4, 4, 0, 0]}>
                    {topZones.map((entry, idx) => (
                      <Cell key={idx} fill={barColor(entry.wait_time, maxBarWt)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
