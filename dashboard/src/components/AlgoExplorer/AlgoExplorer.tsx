import React, { useState } from 'react';
import { AlgorithmCard } from './AlgorithmCard';
import type { AlgorithmItem } from './AlgorithmCard';

interface AlgoExplorerProps {
  algorithms: AlgorithmItem[];
}

export const AlgoExplorer: React.FC<AlgoExplorerProps> = ({ algorithms }) => {
  const [selectedTab, setSelectedTab] = useState<'ALL' | 'CV' | 'SC' | 'NLP' | 'RL'>('ALL');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredAlgos = algorithms.filter((a) => {
    const matchesTab = selectedTab === 'ALL' || a.category === selectedTab;
    const matchesSearch =
      a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      a.id.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesTab && matchesSearch;
  });

  return (
    <div
      style={{
        background: '#030712',
        border: '1px solid rgba(255, 255, 255, 0.1)',
        borderRadius: '10px',
        padding: '20px',
        color: '#f9fafb',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      {/* Title & Stats */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <div>
          <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 700, letterSpacing: '0.02em' }}>
            NEXUSSIM 36-ALGORITHM EXPLORER
          </h3>
          <span style={{ fontSize: '11px', color: '#9ca3af' }}>
            Unified Portfolio across Computer Vision, Soft Computing, NLP & RL
          </span>
        </div>
        <div style={{ display: 'flex', gap: '8px' }}>
          <span style={{ fontSize: '11px', background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8', padding: '3px 8px', borderRadius: '4px', fontWeight: 600 }}>
            12 CV
          </span>
          <span style={{ fontSize: '11px', background: 'rgba(16, 185, 129, 0.15)', color: '#10b981', padding: '3px 8px', borderRadius: '4px', fontWeight: 600 }}>
            12 SC
          </span>
          <span style={{ fontSize: '11px', background: 'rgba(236, 72, 153, 0.15)', color: '#ec4899', padding: '3px 8px', borderRadius: '4px', fontWeight: 600 }}>
            12 NLP
          </span>
          <span style={{ fontSize: '11px', background: 'rgba(139, 92, 246, 0.15)', color: '#8b5cf6', padding: '3px 8px', borderRadius: '4px', fontWeight: 600 }}>
            12 RL
          </span>
        </div>
      </div>

      {/* Tabs and Search Bar */}
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '12px', marginBottom: '16px' }}>
        <div style={{ display: 'flex', gap: '6px' }}>
          {(['ALL', 'CV', 'SC', 'NLP', 'RL'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setSelectedTab(tab)}
              style={{
                background: selectedTab === tab ? '#3b82f6' : 'rgba(255, 255, 255, 0.05)',
                color: selectedTab === tab ? '#fff' : '#9ca3af',
                border: 'none',
                borderRadius: '6px',
                padding: '6px 12px',
                fontSize: '11px',
                fontWeight: 600,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              {tab}
            </button>
          ))}
        </div>

        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search algorithms..."
          style={{
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
            borderRadius: '6px',
            padding: '6px 12px',
            color: '#fff',
            fontSize: '11px',
            width: '200px',
          }}
        />
      </div>

      {/* Grid of Cards */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
          gap: '12px',
          maxHeight: '440px',
          overflowY: 'auto',
          paddingRight: '4px',
        }}
      >
        {filteredAlgos.map((algo) => (
          <AlgorithmCard key={algo.id} algorithm={algo} />
        ))}
      </div>
    </div>
  );
};
