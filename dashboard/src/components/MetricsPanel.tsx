import React from 'react';

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

  return (
    <div style={panelStyle}>
      <h2 style={{ fontSize: '18px', fontWeight: 'bold', margin: '0 0 20px 0', display: 'flex', alignItems: 'center' }}>
        <span style={{ backgroundColor: '#3b82f6', width: '8px', height: '24px', borderRadius: '4px', marginRight: '12px' }}></span>
        Simulation Metrics
      </h2>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div>
          <div style={{ color: '#9ca3af', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '4px' }}>
            Avg Speed
          </div>
          <div style={{ fontSize: '28px', fontWeight: 300 }}>
            {(metrics.avg_speed ?? 0).toFixed(1)} <span style={{ fontSize: '13px', color: '#6b7280' }}>m/s</span>
          </div>
        </div>

        <div style={{ height: '1px', backgroundColor: 'rgba(55, 65, 81, 0.5)', width: '100%' }}></div>

        <div>
          <div style={{ color: '#9ca3af', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '4px' }}>
            Active Agents
          </div>
          <div style={{ fontSize: '28px', fontWeight: 300, color: '#4ade80' }}>
            {metrics.active_agents ?? 0}
          </div>
        </div>

        <div style={{ height: '1px', backgroundColor: 'rgba(55, 65, 81, 0.5)', width: '100%' }}></div>

        <div>
          <div style={{ color: '#9ca3af', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '4px' }}>
            Completed
          </div>
          <div style={{ fontSize: '28px', fontWeight: 300, color: '#3b82f6' }}>
            {metrics.completed_agents ?? 0}
          </div>
        </div>
      </div>
    </div>
  );
};
