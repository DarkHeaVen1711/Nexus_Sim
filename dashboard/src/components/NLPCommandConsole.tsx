import React, { useState } from 'react';

interface NLPCommandConsoleProps {
  onSendMessage: (msg: string) => void;
  simStatus: string | null;
}

export const NLPCommandConsole: React.FC<NLPCommandConsoleProps> = ({ onSendMessage, simStatus }) => {
  const [query, setQuery] = useState('');
  const [history, setHistory] = useState<{ query: string; time: string }[]>([]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    onSendMessage(JSON.stringify({ type: 'nlp_command', command: query.trim() }));
    setHistory(prev => [{ query: query.trim(), time: new Date().toLocaleTimeString() }, ...prev.slice(0, 4)]);
    setQuery('');
  };

  const handlePreset = (preset: string) => {
    setQuery(preset);
  };

  return (
    <div style={{
      position: 'absolute',
      top: 16,
      left: '50%',
      transform: 'translateX(-50%)',
      zIndex: 1000,
      width: 'min(90vw, 640px)',
      display: 'flex',
      flexDirection: 'column',
      gap: '8px'
    }}>
      <form onSubmit={handleSubmit} className="glass-panel" style={{
        display: 'flex',
        alignItems: 'center',
        padding: '6px 10px',
        gap: '8px',
        border: '1px solid rgba(255, 255, 255, 0.12)',
        background: 'rgba(12, 12, 16, 0.85)',
        boxShadow: '0 10px 25px rgba(0, 0, 0, 0.5)'
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '6px',
          padding: '4px 8px',
          background: 'rgba(255, 255, 255, 0.08)',
          borderRadius: '4px',
          fontSize: '11px',
          fontWeight: 600,
          color: '#ffffff',
          letterSpacing: '0.5px'
        }}>
          <span>AI COMMAND</span>
        </div>

        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder='Type natural language query (e.g. "set speed factor 0.8" or "increase chaos 0.4")...'
          style={{
            flex: 1,
            background: 'transparent',
            border: 'none',
            outline: 'none',
            color: '#ffffff',
            fontSize: '13px',
            fontFamily: 'Inter, sans-serif',
            padding: '6px 4px'
          }}
        />

        <button type="submit" className="glass-button-primary" style={{ padding: '6px 12px', fontSize: '12px' }}>
          Execute
        </button>
      </form>

      {/* Preset Quick Actions */}
      <div style={{
        display: 'flex',
        gap: '6px',
        justifyContent: 'center',
        flexWrap: 'wrap'
      }}>
        <button
          onClick={() => handlePreset('set speed factor 0.8')}
          className="glass-button"
          style={{ fontSize: '11px', padding: '4px 8px', background: 'rgba(18, 18, 22, 0.75)' }}
        >
          ⚡ Speed 0.8x
        </button>
        <button
          onClick={() => handlePreset('increase chaos 0.3')}
          className="glass-button"
          style={{ fontSize: '11px', padding: '4px 8px', background: 'rgba(18, 18, 22, 0.75)' }}
        >
          🌧️ Chaos 0.3
        </button>
        <button
          onClick={() => handlePreset('set green time 45s')}
          className="glass-button"
          style={{ fontSize: '11px', padding: '4px 8px', background: 'rgba(18, 18, 22, 0.75)' }}
        >
          🚦 Signal 45s
        </button>
      </div>
    </div>
  );
};
