import React from 'react';
import { CITIES, type CityOption } from '../constants';

interface CitySelectorProps {
  cities?: CityOption[];
  activeCity: string | null;
  disabled?: boolean;
  locked?: boolean;
  locale: string;
  viewMode: 'efficiency' | 'equity';
  onViewModeChange: (mode: 'efficiency' | 'equity') => void;
  onSelect: (city: string) => void;
}

const MENU_STYLE: React.CSSProperties = {
  position: 'absolute',
  top: '60px',
  left: '20px',
  zIndex: 1100,
  backgroundColor: 'rgba(17, 24, 39, 0.95)',
  backdropFilter: 'blur(8px)',
  border: '1px solid #374151',
  borderRadius: '8px',
  color: '#ffffff',
  fontFamily: 'system-ui, sans-serif',
  boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.35)',
  padding: '12px',
  minWidth: '200px',
};

const SECTION_STYLE: React.CSSProperties = {
  color: '#9ca3af',
  fontSize: '11px',
  fontWeight: 600,
  textTransform: 'uppercase',
  letterSpacing: '1px',
  marginBottom: '8px',
};

const cityButtonStyle = (active: boolean, locked: boolean): React.CSSProperties => ({
  display: 'flex',
  width: '100%',
  justifyContent: 'space-between',
  alignItems: 'center',
  padding: '8px 10px',
  marginBottom: '4px',
  textAlign: 'left',
  border: active ? '1px solid #3b82f6' : '1px solid transparent',
  borderRadius: '6px',
  cursor: locked && !active ? 'not-allowed' : 'pointer',
  fontSize: '13px',
  fontWeight: 600,
  fontFamily: 'system-ui, sans-serif',
  textTransform: 'capitalize',
  backgroundColor: active ? 'rgba(59, 130, 246, 0.25)' : 'transparent',
  color: active ? '#ffffff' : '#9ca3af',
  opacity: locked && !active ? 0.45 : 1,
  transition: 'all 0.2s',
});

const viewBtn = (active: boolean): React.CSSProperties => ({
  flex: '1 1 0',
  padding: '6px 0',
  border: active ? '1px solid #3b82f6' : '1px solid #374151',
  borderRadius: '6px',
  cursor: 'pointer',
  fontSize: '12px',
  fontWeight: 600,
  fontFamily: 'system-ui, sans-serif',
  backgroundColor: active ? 'rgba(59, 130, 246, 0.25)' : 'transparent',
  color: active ? '#ffffff' : '#9ca3af',
  transition: 'all 0.2s',
});

export const CitySelector: React.FC<CitySelectorProps> = ({
  cities = CITIES,
  activeCity,
  disabled,
  locked,
  locale,
  viewMode,
  onViewModeChange,
  onSelect,
}) => {
  const [open, setOpen] = React.useState(false);
  const runningCity = activeCity ?? null;

  const toggle = () => setOpen(o => !o);

  return (
    <>
      <button
        onClick={toggle}
        aria-expanded={open}
        aria-label="Dashboard menu"
        style={{
          position: 'absolute',
          top: '20px',
          left: '20px',
          zIndex: 1100,
          width: '44px',
          height: '44px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          border: '1px solid #374151',
          borderRadius: '8px',
          cursor: 'pointer',
          backgroundColor: 'rgba(17, 24, 39, 0.9)',
          color: '#e5e7eb',
          padding: 0,
        }}
      >
        {open ? (
          <svg width={20} height={20} viewBox="0 0 24 24" fill="none"
               stroke="currentColor" strokeWidth="2" strokeLinecap="round"
               strokeLinejoin="round" aria-hidden="true">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        ) : (
          <svg width={20} height={20} viewBox="0 0 24 24" fill="none"
               stroke="currentColor" strokeWidth="2" strokeLinecap="round"
               strokeLinejoin="round" aria-hidden="true">
            <line x1="3" y1="6" x2="21" y2="6" />
            <line x1="3" y1="12" x2="21" y2="12" />
            <line x1="3" y1="18" x2="21" y2="18" />
          </svg>
        )}
      </button>

      {open && (
        <div style={MENU_STYLE}>
          <div style={SECTION_STYLE}>View</div>
          <div style={{ display: 'flex', gap: '6px', marginBottom: '12px' }}>
            <button onClick={() => onViewModeChange('efficiency')} style={viewBtn(viewMode === 'efficiency')}>
              Efficiency
            </button>
            <button onClick={() => onViewModeChange('equity')} style={viewBtn(viewMode === 'equity')}>
              Equity
            </button>
          </div>

          <div style={SECTION_STYLE}>City</div>
          {cities.map((c) => {
            const isActive = runningCity === c.id;
            const isLocked = !!locked && !isActive;
            return (
              <button
                key={c.id}
                onClick={() => { if (!isLocked) onSelect(c.id); }}
                disabled={disabled}
                style={cityButtonStyle(isActive, isLocked)}
                title={locked && runningCity
                  ? `Stop ${runningCity} before switching cities`
                  : undefined}
              >
                <span>{c.label}</span>
                {isActive && <span style={{ fontSize: '10px', color: '#3b82f6' }}>ΓùÅ</span>}
              </button>
            );
          })}

          <div style={{ margin: '10px 0', height: '1px', backgroundColor: 'rgba(107, 114, 128, 0.2)' }} />
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', color: '#6b7280', textTransform: 'uppercase', letterSpacing: '1px' }}>
            <span>Simulation</span>
            <span>{locked && runningCity ? `running ┬╖ ${runningCity}` : 'idle'}</span>
          </div>
          <div style={{ fontSize: '10px', color: '#6b7280', marginTop: '2px' }}>{locale}</div>
        </div>
      )}
    </>
  );
};

export default CitySelector;
