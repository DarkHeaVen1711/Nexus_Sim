import React, { useState, useEffect } from 'react';
import { PauseIcon, PlayIcon, RestartIcon, StopIcon } from './icons';

type SimStatus = 'idle' | 'running' | 'paused' | null;

interface SimControlsProps {
  status: SimStatus;
  city: string | null;
  simTick?: number | null;
  disabled?: boolean;
  onPause: () => void;
  onResume: () => void;
  onRestart: () => void;
  onReset: () => void;
  onScrub?: (targetTick: number) => void;
  onForkScenario?: (tick: number) => void;
}

const BAR_STYLE: React.CSSProperties = {
  position: 'absolute',
  bottom: '20px',
  left: '50%',
  transform: 'translateX(-50%)',
  zIndex: 1000,
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
  backgroundColor: 'rgba(17, 24, 39, 0.95)',
  backdropFilter: 'blur(8px)',
  padding: '8px 14px',
  borderRadius: '12px',
  border: '1px solid #374151',
  boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
  fontFamily: 'system-ui, -apple-system, sans-serif',
};

const btnStyle = (kind: 'pause' | 'resume' | 'restart' | 'reset' | 'fork'): React.CSSProperties => ({
  display: 'flex',
  alignItems: 'center',
  gap: '6px',
  padding: '6px 12px',
  border: '1px solid #374151',
  borderRadius: '7px',
  cursor: 'pointer',
  fontSize: '12px',
  fontWeight: 600,
  fontFamily: 'system-ui, sans-serif',
  transition: 'all 0.2s',
  color: '#e5e7eb',
  backgroundColor:
    kind === 'reset'
      ? 'rgba(239, 68, 68, 0.15)'
      : kind === 'restart'
      ? 'rgba(59, 130, 246, 0.15)'
      : kind === 'fork'
      ? 'rgba(168, 85, 247, 0.15)'
      : 'rgba(34, 197, 94, 0.15)',
  borderColor:
    kind === 'reset'
      ? '#7f1d1d'
      : kind === 'restart'
      ? '#1e3a5f'
      : kind === 'fork'
      ? '#6b21a8'
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
  simTick = 0,
  disabled,
  onPause,
  onResume,
  onRestart,
  onReset,
  onScrub,
  onForkScenario,
}) => {
  const running = status === 'running';
  const paused = status === 'paused';
  const currentTick = simTick ?? 0;
  const [scrubValue, setScrubValue] = useState<number>(currentTick);
  const [isScrubbing, setIsScrubbing] = useState<boolean>(false);

  // Sync scrubber with live simulation tick when not manually dragging
  useEffect(() => {
    if (!isScrubbing) {
      setScrubValue(currentTick);
    }
  }, [currentTick, isScrubbing]);

  const maxTick = Math.max(currentTick, 100);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseInt(e.target.value, 10);
    setScrubValue(val);
    setIsScrubbing(true);
  };

  const handleSliderRelease = () => {
    setIsScrubbing(false);
    if (onScrub) {
      onScrub(scrubValue);
    }
  };

  return (
    <div style={BAR_STYLE}>
      <span
        style={{
          color: '#9ca3af',
          fontSize: '11px',
          fontWeight: 600,
          textTransform: 'uppercase',
          letterSpacing: '1px',
          padding: '0 4px',
        }}
      >
        {city ? city : 'No city'}
      </span>
      <span
        style={{
          width: '9px',
          height: '9px',
          borderRadius: '50%',
          backgroundColor: statusColor(status),
          display: 'inline-block',
          marginRight: '2px',
        }}
      />

      {running && (
        <button onClick={onPause} title="Pause the simulation" style={btnStyle('pause')}>
          <PauseIcon /> Pause
        </button>
      )}

      {paused && (
        <button onClick={onResume} title="Resume the simulation" style={btnStyle('resume')}>
          <PlayIcon /> Resume
        </button>
      )}

      {!running && !paused && (
        <button
          onClick={onPause}
          title="Resume (waiting)"
          disabled
          style={{ ...btnStyle('pause'), opacity: 0.4 }}
        >
          <PauseIcon /> Pause
        </button>
      )}

      <button
        onClick={onRestart}
        disabled={!city || disabled}
        title="Restart the current city from scratch"
        style={{ ...btnStyle('restart'), opacity: !city || disabled ? 0.5 : 1 }}
      >
        <RestartIcon /> Restart
      </button>

      {/* Time-Machine Scrubber Slider */}
      {city && (running || paused || currentTick > 0) && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '0 8px',
            borderLeft: '1px solid #374151',
            borderRight: '1px solid #374151',
          }}
        >
          <span style={{ fontSize: '11px', color: '#9ca3af', minWidth: '65px', textAlign: 'right' }}>
            Tick: <b style={{ color: '#60a5fa' }}>{scrubValue.toLocaleString()}</b>
          </span>
          <input
            type="range"
            min={0}
            max={maxTick}
            value={scrubValue}
            onChange={handleSliderChange}
            onMouseUp={handleSliderRelease}
            onTouchEnd={handleSliderRelease}
            title="Drag timeline to scrub through historical simulation ticks"
            style={{
              width: '130px',
              height: '5px',
              accentColor: '#3b82f6',
              cursor: 'pointer',
            }}
          />
          {onForkScenario && (
            <button
              onClick={() => onForkScenario(scrubValue)}
              title="Fork a divergent what-if scenario at this tick"
              style={btnStyle('fork')}
            >
              <span>⚡</span> Fork
            </button>
          )}
        </div>
      )}

      <button
        onClick={onReset}
        disabled={!city || disabled}
        title="Stop and reset the simulation; unlocks city switching"
        style={{ ...btnStyle('reset'), opacity: !city || disabled ? 0.5 : 1 }}
      >
        <StopIcon /> Reset
      </button>
    </div>
  );
};

export default SimControls;
