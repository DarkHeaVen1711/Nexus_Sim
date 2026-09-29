import React from 'react';

export interface FlowVector {
  x: number;
  y: number;
  vx: number;
  vy: number;
  magnitude: number;
}

interface OpticalFlowPanelProps {
  vectors: FlowVector[];
  meanVelocity: number;
  maxVelocity: number;
  width?: number;
  height?: number;
}

export const OpticalFlowPanel: React.FC<OpticalFlowPanelProps> = ({
  vectors,
  meanVelocity,
  maxVelocity,
  width = 320,
  height = 240,
}) => {
  return (
    <div
      style={{
        background: '#111827',
        borderRadius: '8px',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        padding: '12px',
        color: '#f3f4f6',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '8px',
        }}
      >
        <span style={{ fontSize: '12px', fontWeight: 600, letterSpacing: '0.05em' }}>
          CV-8 OPTICAL FLOW FIELD
        </span>
        <span
          style={{
            fontSize: '10px',
            color: '#9ca3af',
            background: 'rgba(255, 255, 255, 0.05)',
            padding: '2px 6px',
            borderRadius: '4px',
          }}
        >
          {vectors.length} VECTORS
        </span>
      </div>

      <div style={{ display: 'flex', gap: '16px', marginBottom: '8px', fontSize: '11px' }}>
        <div>
          <span style={{ color: '#9ca3af' }}>Mean Flow: </span>
          <strong style={{ color: '#38bdf8' }}>{meanVelocity} px/f</strong>
        </div>
        <div>
          <span style={{ color: '#9ca3af' }}>Peak Flow: </span>
          <strong style={{ color: '#f43f5e' }}>{maxVelocity} px/f</strong>
        </div>
      </div>

      <svg
        width={width}
        height={height}
        style={{
          background: '#030712',
          borderRadius: '4px',
          display: 'block',
          width: '100%',
        }}
        viewBox={`0 0 ${width} ${height}`}
      >
        {vectors.map((v, i) => {
          const color = v.magnitude > 5.0 ? '#f43f5e' : v.magnitude > 2.0 ? '#f59e0b' : '#38bdf8';
          return (
            <line
              key={i}
              x1={v.x}
              y1={v.y}
              x2={v.x + v.vx * 2.5}
              y2={v.y + v.vy * 2.5}
              stroke={color}
              strokeWidth={1.5}
              strokeLinecap="round"
            />
          );
        })}
      </svg>
    </div>
  );
};
