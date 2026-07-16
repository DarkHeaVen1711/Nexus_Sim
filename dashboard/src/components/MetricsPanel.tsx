import React from 'react';

interface MetricsPanelProps {
  metrics: {
    avg_wait_time: number;
    gini_coefficient: number;
  } | null;
}

export const MetricsPanel: React.FC<MetricsPanelProps> = ({ metrics }) => {
  if (!metrics) return null;

  const getGiniColor = (val: number) => {
    if (val < 0.3) return '#4ade80'; // green
    if (val < 0.5) return '#facc15'; // yellow
    return '#f87171'; // red
  };

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
    width: '320px',
    fontFamily: 'system-ui, sans-serif'
  };

  return (
    <div style={panelStyle}>
      <h2 style={{ fontSize: '20px', fontWeight: 'bold', margin: '0 0 24px 0', display: 'flex', alignItems: 'center' }}>
        <span style={{ backgroundColor: '#3b82f6', width: '8px', height: '24px', borderRadius: '4px', marginRight: '12px' }}></span>
        Simulation Metrics
      </h2>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
        <div>
          <div style={{ color: '#9ca3af', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '4px' }}>
            Efficiency
          </div>
          <div style={{ fontSize: '32px', fontWeight: 300 }}>
            {metrics.avg_wait_time.toFixed(1)} <span style={{ fontSize: '14px', color: '#6b7280' }}>sec/veh</span>
          </div>
          <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px' }}>Citywide Avg. Wait Time</div>
        </div>

        <div style={{ height: '1px', backgroundColor: 'rgba(55, 65, 81, 0.5)', width: '100%' }}></div>

        <div>
          <div style={{ color: '#9ca3af', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '4px' }}>
            Equity
          </div>
          <div style={{ fontSize: '32px', fontWeight: 300, color: getGiniColor(metrics.gini_coefficient) }}>
            {metrics.gini_coefficient.toFixed(3)}
          </div>
          <div style={{ fontSize: '11px', color: '#6b7280', marginTop: '4px' }}>Gini Coefficient (0=Equal, 1=Unequal)</div>
          
          <div style={{ marginTop: '12px', height: '8px', width: '100%', backgroundColor: '#1f2937', borderRadius: '4px', overflow: 'hidden', display: 'flex' }}>
            <div 
              style={{ 
                height: '100%', 
                backgroundColor: getGiniColor(metrics.gini_coefficient),
                width: `${Math.min(100, metrics.gini_coefficient * 100)}%` 
              }}
            ></div>
          </div>
        </div>
      </div>
    </div>
  );
};
