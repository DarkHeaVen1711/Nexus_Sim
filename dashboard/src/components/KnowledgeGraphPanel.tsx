import React from 'react';

interface KGNode {
  data: { id: string; label: string };
}

interface KGEdge {
  data: { id: string; source: string; target: string; label: string };
}

interface KnowledgeGraphPanelProps {
  graphData: {
    nodes: KGNode[];
    edges: KGEdge[];
  };
}

export const KnowledgeGraphPanel: React.FC<KnowledgeGraphPanelProps> = ({ graphData }) => {
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
          NLP-12 TRAFFIC KNOWLEDGE GRAPH (KG)
        </h4>
        <span style={{ fontSize: '10px', color: '#ec4899', background: 'rgba(236, 72, 153, 0.1)', padding: '2px 6px', borderRadius: '4px' }}>
          {graphData.nodes.length} ENTITIES | {graphData.edges.length} RELATIONS
        </span>
      </div>

      <div
        style={{
          background: '#030712',
          padding: '12px',
          borderRadius: '6px',
          maxHeight: '220px',
          overflowY: 'auto',
          fontSize: '11px',
          fontFamily: 'monospace',
        }}
      >
        <div style={{ color: '#9ca3af', marginBottom: '8px' }}>Active Relational Triples (RDF):</div>
        {graphData.edges.map((edge) => (
          <div
            key={edge.data.id}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 0',
              borderBottom: '1px solid rgba(255, 255, 255, 0.05)',
            }}
          >
            <span style={{ color: '#38bdf8', fontWeight: 'bold' }}>({edge.data.source})</span>
            <span style={{ color: '#ec4899' }}>--[{edge.data.label}]--&gt;</span>
            <span style={{ color: '#34d399', fontWeight: 'bold' }}>({edge.data.target})</span>
          </div>
        ))}
      </div>
    </div>
  );
};
