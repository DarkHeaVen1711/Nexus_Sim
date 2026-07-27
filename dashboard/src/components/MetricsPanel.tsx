import React from 'react';
import { giniLabel, giniColor } from '../constants';

interface MetricsPanelProps {
  metrics: {
    avg_speed?: number;
    active_agents?: number;
    completed_agents?: number;
    avg_wait_time?: number;
    gini_coefficient?: number;
  } | null;
}

export const MetricsPanel: React.FC<MetricsPanelProps> = ({ metrics }) => {
  if (!metrics) return null;

  const gini = metrics.gini_coefficient ?? 0;
  const waitTime = metrics.avg_wait_time ?? 0;

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
    width: '280px',
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
      </h2>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div>
          <div style={labelStyle}>Avg Speed</div>
          <div style={valueStyle}>{(metrics.avg_speed ?? 0).toFixed(1)} <span style={{ fontSize: '13px', color: '#6b7280' }}>m/s</span></div>
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
      </div>
    </div>
  );
};
