import React, { useState } from 'react';

interface IncidentReportPanelProps {
  city?: string | null;
  visible?: boolean;
}

export const IncidentReportPanel: React.FC<IncidentReportPanelProps> = ({
  city = 'chicago',
  visible = true,
}) => {
  const [text, setText] = useState('');
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!visible) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim() || submitting) return;

    setSubmitting(true);
    setStatusMsg(null);

    fetch('http://localhost:9004/incident', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text: text.trim(), city: city || 'chicago' }),
    })
      .then((res) => {
        if (!res.ok) throw new Error('NLP service offline');
        return res.json();
      })
      .then((data) => {
        setStatusMsg(`✅ ${data.message}`);
        setText('');
        setSubmitting(false);
      })
      .catch(() => {
        setStatusMsg(`[Offline] Simulated incident mutation registered for "${text.trim()}".`);
        setText('');
        setSubmitting(false);
      });
  };

  return (
    <div
      style={{
        backgroundColor: 'rgba(17, 24, 39, 0.95)',
        border: '1px solid rgba(107, 114, 128, 0.3)',
        borderRadius: '12px',
        padding: '14px',
        color: '#ffffff',
        fontFamily: 'system-ui, sans-serif',
        width: '100%',
        boxSizing: 'border-box',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: '10px' }}>
        <span
          style={{
            backgroundColor: '#ef4444',
            width: '8px',
            height: '22px',
            borderRadius: '4px',
            marginRight: '10px',
          }}
        ></span>
        <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 700 }}>
          NLP Incident Mutation Report
        </h3>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="e.g. Major accident blocking Michigan Ave for 10 minutes"
          rows={3}
          style={{
            backgroundColor: '#1f2937',
            border: '1px solid #374151',
            borderRadius: '6px',
            padding: '8px',
            color: '#ffffff',
            fontSize: '11px',
            resize: 'none',
          }}
        />
        <button
          type="submit"
          disabled={submitting}
          style={{
            backgroundColor: '#ef4444',
            border: 'none',
            borderRadius: '6px',
            color: '#ffffff',
            padding: '6px 12px',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Inject Incident Mutation
        </button>
      </form>

      {statusMsg && (
        <div style={{ fontSize: '10px', color: '#f87171', marginTop: '8px', lineHeight: '1.4' }}>
          {statusMsg}
        </div>
      )}
    </div>
  );
};

export default IncidentReportPanel;
