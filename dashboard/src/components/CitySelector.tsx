import React from 'react';
import { CITIES, type CityOption } from '../constants';

interface CitySelectorProps {
  cities?: CityOption[];
  activeCity: string | null;
  disabled?: boolean;
  onSelect: (city: string) => void;
}

const buttonStyle = (active: boolean, disabled: boolean): React.CSSProperties => ({
  padding: '8px 16px',
  border: '1px solid #374151',
  borderRadius: '6px',
  cursor: disabled ? 'wait' : 'pointer',
  fontSize: '13px',
  fontWeight: 600,
  fontFamily: 'system-ui, sans-serif',
  textTransform: 'capitalize',
  backgroundColor: active ? '#3b82f6' : 'rgba(17, 24, 39, 0.85)',
  color: active ? '#ffffff' : '#9ca3af',
  opacity: disabled && !active ? 0.6 : 1,
  transition: 'all 0.2s',
});

export const CitySelector: React.FC<CitySelectorProps> = ({
  cities = CITIES,
  activeCity,
  disabled,
  onSelect,
}) => {
  return (
    <div
      style={{
        position: 'absolute',
        top: '20px',
        left: '50%',
        transform: 'translateX(-50%)',
        zIndex: 1000,
        display: 'flex',
        alignItems: 'center',
        gap: '4px',
        backgroundColor: 'rgba(17, 24, 39, 0.9)',
        padding: '4px',
        borderRadius: '8px',
        border: '1px solid #374151',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      <span style={{ color: '#9ca3af', fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '1px', padding: '0 8px' }}>
        City
      </span>
      {cities.map((c) => (
        <button
          key={c.id}
          onClick={() => onSelect(c.id)}
          disabled={disabled}
          style={buttonStyle(activeCity === c.id, !!disabled)}
        >
          {c.label}
        </button>
      ))}
    </div>
  );
};

export default CitySelector;
