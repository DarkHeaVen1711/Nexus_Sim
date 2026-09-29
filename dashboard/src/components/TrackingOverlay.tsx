import React from 'react';

export interface TrackedVehicle {
  track_id: number;
  bbox: [number, number, number, number]; // [x, y, w, h]
  hits: number;
  age: number;
}

interface TrackingOverlayProps {
  tracks: TrackedVehicle[];
  width?: number;
  height?: number;
  roadCondition?: 'DRY' | 'WET' | 'HAZARDOUS';
}

export const TrackingOverlay: React.FC<TrackingOverlayProps> = ({
  tracks,
  width = 640,
  height = 480,
  roadCondition = 'DRY',
}) => {
  const badgeColor =
    roadCondition === 'HAZARDOUS' ? '#ef4444' : roadCondition === 'WET' ? '#3b82f6' : '#10b981';

  return (
    <div
      style={{
        position: 'relative',
        width: '100%',
        maxWidth: `${width}px`,
        height: `${height}px`,
        background: '#111827',
        borderRadius: '8px',
        overflow: 'hidden',
        border: '1px solid rgba(255, 255, 255, 0.1)',
      }}
    >
      {/* Header telemetry */}
      <div
        style={{
          position: 'absolute',
          top: 8,
          left: 12,
          right: 12,
          display: 'flex',
          justifyContent: 'space-between',
          zIndex: 10,
          fontSize: '11px',
          color: '#e5e7eb',
          fontFamily: 'monospace',
          background: 'rgba(0, 0, 0, 0.6)',
          padding: '4px 8px',
          borderRadius: '4px',
        }}
      >
        <span>ACTIVE TRACKS: {tracks.length}</span>
        <span>
          CV-7 ROAD SURFACE:{' '}
          <strong style={{ color: badgeColor }}>{roadCondition}</strong>
        </span>
      </div>

      {/* Track bounding boxes */}
      <svg
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
        }}
        viewBox={`0 0 ${width} ${height}`}
      >
        {tracks.map((t) => {
          const [x, y, w, h] = t.bbox;
          return (
            <g key={t.track_id}>
              <rect
                x={x}
                y={y}
                width={w}
                height={h}
                fill="none"
                stroke="#22c55e"
                strokeWidth={1.5}
                strokeDasharray="2,2"
              />
              <rect
                x={x}
                y={Math.max(0, y - 14)}
                width={w > 40 ? w : 40}
                height={14}
                fill="#22c55e"
                opacity={0.85}
              />
              <text
                x={x + 3}
                y={Math.max(10, y - 3)}
                fill="#000"
                fontSize={9}
                fontWeight="bold"
                fontFamily="monospace"
              >
                ID #{t.track_id}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
};
