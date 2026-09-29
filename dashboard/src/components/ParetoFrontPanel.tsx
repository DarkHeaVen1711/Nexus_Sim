import React, { useState } from 'react';

export interface ParetoPoint {
  id: number;
  wait_time_s: number;
  gini_coefficient: number;
  parameters: {
    alpha_efficiency: number;
    beta_equity: number;
    speed_factor: number;
    chaos: number;
  };
}

interface ParetoFrontPanelProps {
  solutions: ParetoPoint[];
  onSelectSolution?: (solution: ParetoPoint) => void;
}

export const ParetoFrontPanel: React.FC<ParetoFrontPanelProps> = ({
  solutions,
  onSelectSolution,
}) => {
  const [selectedId, setSelectedId] = useState<number | null>(solutions[0]?.id ?? null);

  const selectedPoint = solutions.find((s) => s.id === selectedId) || solutions[0];

  return (
    <div
      style={{
        background: '#111827',
        borderRadius: '8px',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        padding: '16px',
        color: '#f3f4f6',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
        <h4 style={{ margin: 0, fontSize: '13px', fontWeight: 600 }}>
          NSGA-II PARETO FRONTIER (EFFICIENCY VS EQUITY)
        </h4>
        <span style={{ fontSize: '10px', color: '#10b981', background: 'rgba(16, 185, 129, 0.1)', padding: '2px 6px', borderRadius: '4px' }}>
          {solutions.length} OPTIMAL POINTS
        </span>
      </div>

      {/* SVG Scatter Plot */}
      <svg
        width="100%"
        height="180"
        viewBox="0 0 340 180"
        style={{ background: '#030712', borderRadius: '6px', marginBottom: '12px' }}
      >
        {/* Grid and Axis Labels */}
        <text x="12" y="15" fill="#9ca3af" fontSize="9">
          Gini Index (Equity)
        </text>
        <text x="230" y="172" fill="#9ca3af" fontSize="9">
          Wait Time (s)
        </text>

        {solutions.map((pt) => {
          // Normalize coordinates
          const cx = 35 + ((pt.wait_time_s - 25.0) / 20.0) * 270;
          const cy = 150 - ((pt.gini_coefficient - 0.2) / 0.3) * 125;
          const isSelected = pt.id === selectedId;

          return (
            <circle
              key={pt.id}
              cx={Math.max(25, Math.min(320, cx))}
              cy={Math.max(25, Math.min(160, cy))}
              r={isSelected ? 6 : 4}
              fill={isSelected ? '#38bdf8' : '#6366f1'}
              stroke={isSelected ? '#ffffff' : 'none'}
              strokeWidth={1.5}
              style={{ cursor: 'pointer', transition: 'all 0.2s ease' }}
              onClick={() => {
                setSelectedId(pt.id);
                if (onSelectSolution) onSelectSolution(pt);
              }}
            />
          );
        })}
      </svg>

      {/* Selected Parameters Detail */}
      {selectedPoint && (
        <div
          style={{
            background: 'rgba(255, 255, 255, 0.03)',
            padding: '10px 12px',
            borderRadius: '6px',
            fontSize: '11px',
            display: 'flex',
            justifyContent: 'space-between',
          }}
        >
          <div>
            <div style={{ color: '#9ca3af' }}>Solution #{selectedPoint.id}</div>
            <div style={{ fontWeight: 600, color: '#38bdf8' }}>
              Wait: {selectedPoint.wait_time_s}s | Gini: {selectedPoint.gini_coefficient}
            </div>
          </div>
          <div style={{ fontFamily: 'monospace', textAlign: 'right', color: '#d1d5db' }}>
            α={selectedPoint.parameters.alpha_efficiency} | β={selectedPoint.parameters.beta_equity}
            <br />
            speed={selectedPoint.parameters.speed_factor}
          </div>
        </div>
      )}
    </div>
  );
};
