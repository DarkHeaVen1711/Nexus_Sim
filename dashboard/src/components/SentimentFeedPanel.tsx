import React, { useState } from 'react';

export interface CitizenFeedbackItem {
  id: string;
  text: string;
  sentiment: 'POSITIVE' | 'NEUTRAL' | 'NEGATIVE';
  frustration: number; // 0..1
  category: string;
  time: string;
}

interface SentimentFeedPanelProps {
  feed: CitizenFeedbackItem[];
  onSubmitFeedback?: (text: string) => void;
}

export const SentimentFeedPanel: React.FC<SentimentFeedPanelProps> = ({
  feed,
  onSubmitFeedback,
}) => {
  const [inputText, setInputText] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputText.trim() && onSubmitFeedback) {
      onSubmitFeedback(inputText.trim());
      setInputText('');
    }
  };

  const getSentimentColor = (sentiment: string) => {
    if (sentiment === 'POSITIVE') return '#10b981';
    if (sentiment === 'NEGATIVE') return '#ef4444';
    return '#9ca3af';
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
          NLP-3 CITIZEN SENTIMENT & FEEDBACK
        </h4>
        <span style={{ fontSize: '10px', color: '#38bdf8', background: 'rgba(56, 189, 248, 0.1)', padding: '2px 6px', borderRadius: '4px' }}>
          LIVE NLP FEED
        </span>
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Report traffic condition, bottleneck, or praise..."
          style={{
            flex: 1,
            background: 'rgba(0, 0, 0, 0.3)',
            border: '1px solid rgba(255, 255, 255, 0.15)',
            borderRadius: '4px',
            padding: '6px 10px',
            color: '#fff',
            fontSize: '11px',
          }}
        />
        <button
          type="submit"
          style={{
            background: '#3b82f6',
            color: '#fff',
            border: 'none',
            borderRadius: '4px',
            padding: '6px 12px',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Submit
        </button>
      </form>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '200px', overflowY: 'auto' }}>
        {feed.map((item) => (
          <div
            key={item.id}
            style={{
              background: 'rgba(255, 255, 255, 0.02)',
              borderRadius: '6px',
              padding: '8px 10px',
              borderLeft: `3px solid ${getSentimentColor(item.sentiment)}`,
              fontSize: '11px',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
              <span style={{ fontWeight: 600, color: getSentimentColor(item.sentiment) }}>
                {item.sentiment} ({item.category})
              </span>
              <span style={{ color: '#6b7280', fontSize: '10px' }}>{item.time}</span>
            </div>
            <div style={{ color: '#d1d5db', marginBottom: '4px' }}>"{item.text}"</div>
            {item.frustration > 0.4 && (
              <div style={{ fontSize: '10px', color: '#f87171' }}>
                Frustration index: {(item.frustration * 100).toFixed(0)}%
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
