import React from 'react';

interface FuzzyRuleActivation {
  ruleIndex: number;
  condition: string;
  consequent: string;
  activation: number; // 0..1
}

interface FuzzyRulesPanelProps {
  activations: FuzzyRuleActivation[];
  activePolicy: 'MAMDANI' | 'ANFIS' | 'TYPE2_FUZZY';
  greenExtensionSeconds: number;
}

export const FuzzyRulesPanel: React.FC<FuzzyRulesPanelProps> = ({
  activations,
  activePolicy,
  greenExtensionSeconds,
}) => {
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
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h4 style={{ margin: 0, fontSize: '13px', fontWeight: 600 }}>
          FUZZY INFERENCE ACTIVATIONS ({activePolicy})
        </h4>
        <span
          style={{
            fontSize: '11px',
            color: '#10b981',
            background: 'rgba(16, 185, 129, 0.1)',
            padding: '3px 8px',
            borderRadius: '4px',
            fontWeight: 'bold',
          }}
        >
          +{greenExtensionSeconds.toFixed(1)}s GREEN EXTENSION
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {activations.map((r) => (
          <div
            key={r.ruleIndex}
            style={{
              background: 'rgba(255, 255, 255, 0.02)',
              borderRadius: '4px',
              padding: '6px 10px',
              fontSize: '11px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span>
                <strong>R{r.ruleIndex}:</strong> IF {r.condition} THEN {r.consequent}
              </span>
              <span style={{ color: '#38bdf8', fontFamily: 'monospace' }}>
                {(r.activation * 100).toFixed(0)}%
              </span>
            </div>
            {/* Progress bar */}
            <div
              style={{
                width: '100%',
                height: '4px',
                background: 'rgba(255, 255, 255, 0.08)',
                borderRadius: '2px',
                overflow: 'hidden',
              }}
            >
              <div
                style={{
                  width: `${Math.min(100, r.activation * 100)}%`,
                  height: '100%',
                  background: r.activation > 0.6 ? '#10b981' : r.activation > 0.2 ? '#38bdf8' : '#6b7280',
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
