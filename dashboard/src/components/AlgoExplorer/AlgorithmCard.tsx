import React from 'react';

export interface AlgorithmItem {
  id: string;
  name: string;
  category: 'CV' | 'SC' | 'NLP' | 'RL';
  status: string;
  latency_ms: number;
  accuracy?: string;
  metric?: string;
}

interface AlgorithmCardProps {
  algorithm: AlgorithmItem;
}

export const AlgorithmCard: React.FC<AlgorithmCardProps> = ({ algorithm }) => {
  const getCategoryColor = (cat: string) => {
    switch (cat) {
      case 'CV':
        return '#38bdf8';
      case 'SC':
        return '#10b981';
      case 'NLP':
        return '#ec4899';
      case 'RL':
        return '#8b5cf6';
      default:
        return '#9ca3af';
    }
  };

  const isActive = algorithm.status === 'ACTIVE' || algorithm.status.includes('DEPLOYED');

  return (
    <div
      style={{
        background: '#111827',
        border: '1px solid rgba(255, 255, 255, 0.08)',
        borderRadius: '8px',
        padding: '12px 14px',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        position: 'relative',
        boxShadow: '0 2px 4px rgba(0, 0, 0, 0.2)',
      }}
    >
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
          <span
            style={{
              fontSize: '10px',
              fontWeight: 700,
              padding: '2px 6px',
              borderRadius: '4px',
              background: `${getCategoryColor(algorithm.category)}20`,
              color: getCategoryColor(algorithm.category),
              fontFamily: 'monospace',
            }}
          >
            {algorithm.id}
          </span>
          <span
            style={{
              fontSize: '9px',
              padding: '1px 5px',
              borderRadius: '3px',
              background: isActive ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)',
              color: isActive ? '#34d399' : '#f87171',
              fontWeight: 600,
            }}
          >
            {algorithm.status}
          </span>
        </div>
        <div style={{ fontSize: '12px', fontWeight: 600, color: '#f3f4f6', marginBottom: '8px' }}>
          {algorithm.name}
        </div>
      </div>

      <div style={{ fontSize: '11px', color: '#9ca3af', borderTop: '1px solid rgba(255, 255, 255, 0.05)', paddingTop: '8px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '2px' }}>
          <span>Latency:</span>
          <strong style={{ color: '#e5e7eb' }}>{algorithm.latency_ms} ms</strong>
        </div>
        {algorithm.accuracy && (
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>Accuracy:</span>
            <strong style={{ color: '#38bdf8' }}>{algorithm.accuracy}</strong>
          </div>
        )}
        {algorithm.metric && (
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <span>Metric:</span>
            <strong style={{ color: '#34d399' }}>{algorithm.metric}</strong>
          </div>
        )}
      </div>
    </div>
  );
};
