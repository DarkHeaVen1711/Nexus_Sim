import React from 'react';
import { PauseIcon, PlayIcon, RestartIcon, StopIcon } from './icons';

type SimStatus = 'idle' | 'running' | 'paused' | null;

interface SimControlsProps {
  status: SimStatus;
  city: string | null;
  disabled?: boolean;
  onPause: () => void;
  onResume: () => void;
  onRestart: () => void;
  onReset: () => void;
}

const BAR_STYLE: React.CSSProperties = {
  position: 'absolute',
  bottom: '20px',
  left: '50%',
  transform: 'translateX(-50%)',
  zIndex: 1000,
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
  backgroundColor: 'rgba(17, 24, 39, 0.9)',
  padding: '6px',
  borderRadius: '10px',
  border: '1px solid #374151',
  fontFamily: 'system-ui, sans-serif',
};

const btnStyle = (kind: 'pause' | 'resume' | 'restart' | 'reset'): React.CSSProperties => ({
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
  padding: '7px 14px',
  border: '1px solid #374151',
  borderRadius: '7px',
  cursor: 'pointer',
  fontSize: '12px',
  fontWeight: 600,
  fontFamily: 'system-ui, sans-serif',
  transition: 'all 0.2s',
  color: '#e5e7eb',
  backgroundColor: kind === 'reset'
    ? 'rgba(239, 68, 68, 0.15)'
    : kind === 'restart'
      ? 'rgba(59, 130, 246, 0.15)'
      : 'rgba(34, 197, 94, 0.15)',
  borderColor: kind === 'reset'
    ? '#7f1d1d'
    : kind === 'restart'
      ? '#1e3a5f'
      : '#14532d',
});

const statusColor = (status: SimStatus): string => {
  if (status === 'paused') return '#fbbf24';
  if (status === 'running') return '#4ade80';
  return '#6b7280';
};

export const SimControls: React.FC<SimControlsProps> = ({
  status,
  city,
  disabled,
  onPause,
  onResume,
  onRestart,
  onReset,
}) => {
  const running = status === 'running';
  const paused = status === 'paused';

  return (
    <div style={BAR_STYLE}>
      <span style={{
        color: '#9ca3af',
        fontSize: '11px',
        fontWeight: 600,
        textTransform: 'uppercase',
        letterSpacing: '1px',
        padding: '0 8px',
      }}>
        {city ? city : 'No city'}
      </span>
      <span style={{
        width: '9px',
        height: '9px',
        borderRadius: '50%',
        backgroundColor: statusColor(status),
        display: 'inline-block',
        marginRight: '4px',
      }} />

      {running && (
        <button onClick={onPause} title="Pause the simulation"
                style={btnStyle('pause')}>
          <PauseIcon /> Pause
        </button>
      )}

      {paused && (
        <button onClick={onResume} title="Resume the simulation"
                style={btnStyle('resume')}>
          <PlayIcon /> Resume
        </button>
      )}

      {!running && !paused && (
        <button onClick={onPause} title="Resume (waiting)" disabled
                style={{ ...btnStyle('pause'), opacity: 0.4 }}>
          <PauseIcon /> Pause
        </button>
      )}

      <button onClick={onRestart} disabled={!city || disabled}
              title="Restart the current city from scratch"
              style={{ ...btnStyle('restart'), opacity: !city || disabled ? 0.5 : 1 }}>
        <RestartIcon /> Restart
      </button>

      <button onClick={onReset} disabled={!city || disabled}
              title="Stop and reset the simulation; unlocks city switching"
              style={{ ...btnStyle('reset'), opacity: !city || disabled ? 0.5 : 1 }}>
        <StopIcon /> Reset
      </button>
    </div>
  );
};

export default SimControls;