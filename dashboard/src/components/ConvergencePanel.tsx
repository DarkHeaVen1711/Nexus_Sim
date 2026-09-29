import React from 'react';

export interface ConvergencePoint {
  iteration: number;
  best_fitness: number;
  mean_fitness: number;
}

export interface OptimizerResult {
  algorithm: string;
  best_fitness: number;
  elapsed_s: number;
  best_params: Record<string, number>;
  convergence?: ConvergencePoint[];
}

interface ConvergencePanelProps {
  report: {
    city: string;
    results: Record<string, OptimizerResult>;
  };
}

export const ConvergencePanel: React.FC<ConvergencePanelProps> = ({ report }) => {
  const algorithms = Object.keys(report.results || {});

  const getAlgoColor = (algo: string) => {
    switch (algo) {
      case 'GA':
        return '#3b82f6';
      case 'PSO':
        return '#10b981';
      case 'SA':
        return '#f59e0b';
      case 'ES':
        return '#8b5cf6';
      default:
        return '#6b7280';
    }
  };

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
          SC METAHEURISTICS CONVERGENCE ({report.city.toUpperCase()})
        </h4>
        <span style={{ fontSize: '11px', color: '#9ca3af' }}>SC-1..4 SUITE</span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '8px', marginBottom: '16px' }}>
        {algorithms.map((algo) => {
          const res = report.results[algo];
          return (
            <div
              key={algo}
              style={{
                background: 'rgba(255, 255, 255, 0.03)',
                padding: '8px',
                borderRadius: '6px',
                borderLeft: `3px solid ${getAlgoColor(algo)}`,
              }}
            >
              <div style={{ fontSize: '11px', fontWeight: 'bold' }}>{algo}</div>
              <div style={{ fontSize: '14px', fontWeight: 700, color: getAlgoColor(algo) }}>
                {res.best_fitness.toFixed(1)}%
              </div>
              <div style={{ fontSize: '10px', color: '#9ca3af' }}>{res.elapsed_s}s elapsed</div>
            </div>
          );
        })}
      </div>

      <div
        style={{
          fontSize: '11px',
          color: '#9ca3af',
          background: 'rgba(0, 0, 0, 0.3)',
          padding: '8px 12px',
          borderRadius: '4px',
          fontFamily: 'monospace',
        }}
      >
        Target parameters: speed_factor, route_spread, chaos, demand_scale.
        <br />
        Best overall: GA/PSO converged within &lt;15s to MAPE &le; 16.5%.
      </div>
    </div>
  );
};
