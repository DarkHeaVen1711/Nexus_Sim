import React from 'react';

export interface ExtractedEntity {
  entity: string;
  label: 'LOCATION' | 'VEHICLE' | 'DURATION' | 'SEVERITY';
  start: number;
  end: number;
}

interface NERPanelProps {
  originalText: string;
  entities: ExtractedEntity[];
  eventTuple?: {
    action: string;
    location: string;
    severity: number;
    duration_s: number;
    speed_multiplier: number;
  };
}

export const NERPanel: React.FC<NERPanelProps> = ({
  originalText,
  entities,
  eventTuple,
}) => {
  const getBadgeStyle = (label: string) => {
    switch (label) {
      case 'LOCATION':
        return { background: 'rgba(56, 189, 248, 0.2)', color: '#38bdf8', border: '1px solid #38bdf8' };
      case 'VEHICLE':
        return { background: 'rgba(52, 211, 153, 0.2)', color: '#34d399', border: '1px solid #34d399' };
      case 'DURATION':
        return { background: 'rgba(251, 191, 36, 0.2)', color: '#fbbf24', border: '1px solid #fbbf24' };
      case 'SEVERITY':
        return { background: 'rgba(244, 63, 94, 0.2)', color: '#f43f5e', border: '1px solid #f43f5e' };
      default:
        return { background: 'rgba(156, 163, 175, 0.2)', color: '#9ca3af', border: '1px solid #9ca3af' };
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
          NLP-7/8 NAMED ENTITY RECOGNITION & EVENT EXTRACTION
        </h4>
        <span style={{ fontSize: '10px', color: '#a78bfa', background: 'rgba(167, 139, 250, 0.1)', padding: '2px 6px', borderRadius: '4px' }}>
          {entities.length} ENTITIES EXTRACTED
        </span>
      </div>

      {/* Raw annotated view */}
      <div
        style={{
          background: 'rgba(0, 0, 0, 0.3)',
          padding: '10px',
          borderRadius: '4px',
          fontSize: '11px',
          marginBottom: '12px',
          lineHeight: '1.6',
        }}
      >
        <span style={{ color: '#9ca3af' }}>Source: </span>
        "{originalText}"
      </div>

      {/* Entity badges */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', marginBottom: '12px' }}>
        {entities.map((ent, idx) => {
          const style = getBadgeStyle(ent.label);
          return (
            <span
              key={idx}
              style={{
                fontSize: '10px',
                padding: '2px 6px',
                borderRadius: '4px',
                fontWeight: 500,
                ...style,
              }}
            >
              {ent.entity} [{ent.label}]
            </span>
          );
        })}
      </div>

      {/* Executable Tuple Summary */}
      {eventTuple && (
        <div
          style={{
            background: 'rgba(255, 255, 255, 0.02)',
            borderLeft: '3px solid #38bdf8',
            padding: '8px 12px',
            borderRadius: '4px',
            fontSize: '11px',
          }}
        >
          <div style={{ fontWeight: 600, color: '#38bdf8', marginBottom: '2px' }}>
            Actionable Engine Mutation Event:
          </div>
          <div style={{ fontFamily: 'monospace', color: '#e5e7eb' }}>
            apply_incident(loc="{eventTuple.location}", action={eventTuple.action}, sev={eventTuple.severity}, dur={eventTuple.duration_s}s, speed_mult={eventTuple.speed_multiplier})
          </div>
        </div>
      )}
    </div>
  );
};
