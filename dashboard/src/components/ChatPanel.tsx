import React, { useState } from 'react';

interface ChatMessage {
  sender: 'user' | 'bot';
  text: string;
  intent?: string;
}

interface ChatPanelProps {
  city?: string | null;
  visible?: boolean;
}

export const ChatPanel: React.FC<ChatPanelProps> = ({ city = 'chicago', visible = true }) => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { sender: 'bot', text: 'Hello! Ask me anything about live traffic metrics, worst zones, or signal policies.' },
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);

  if (!visible) return null;

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { sender: 'user', text: userText }]);
    setLoading(true);

    fetch('http://localhost:9001/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query: userText, city: city || 'chicago' }),
    })
      .then((res) => {
        if (!res.ok) throw new Error('NLP service offline');
        return res.json();
      })
      .then((data) => {
        setMessages((prev) => [
          ...prev,
          { sender: 'bot', text: data.answer, intent: data.intent },
        ]);
        setLoading(false);
      })
      .catch(() => {
        setMessages((prev) => [
          ...prev,
          {
            sender: 'bot',
            text: `[Offline Mode] Simulated response for "${userText}": Active citywide average speed is 32.4 km/h with 542 active agents.`,
            intent: 'offline_fallback',
          },
        ]);
        setLoading(false);
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
            backgroundColor: '#6366f1',
            width: '8px',
            height: '22px',
            borderRadius: '4px',
            marginRight: '10px',
          }}
        ></span>
        <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 700 }}>
          NLP Live Metrics Chat (Port 9001)
        </h3>
      </div>

      <div
        style={{
          height: '140px',
          overflowY: 'auto',
          backgroundColor: 'rgba(31, 41, 55, 0.6)',
          borderRadius: '8px',
          padding: '10px',
          marginBottom: '10px',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
        }}
      >
        {messages.map((m, idx) => (
          <div
            key={idx}
            style={{
              alignSelf: m.sender === 'user' ? 'flex-end' : 'flex-start',
              backgroundColor: m.sender === 'user' ? '#4f46e5' : '#374151',
              padding: '6px 10px',
              borderRadius: '8px',
              fontSize: '11px',
              maxWidth: '85%',
              lineHeight: '1.4',
            }}
          >
            {m.text}
            {m.intent && (
              <div style={{ fontSize: '9px', color: '#a5b4fc', marginTop: '2px' }}>
                Intent: {m.intent}
              </div>
            )}
          </div>
        ))}
      </div>

      <form onSubmit={handleSend} style={{ display: 'flex', gap: '6px' }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask e.g. worst zone?"
          style={{
            flex: 1,
            backgroundColor: '#1f2937',
            border: '1px solid #374151',
            borderRadius: '6px',
            padding: '6px 10px',
            color: '#ffffff',
            fontSize: '11px',
          }}
        />
        <button
          type="submit"
          disabled={loading}
          style={{
            backgroundColor: '#6366f1',
            border: 'none',
            borderRadius: '6px',
            color: '#ffffff',
            padding: '6px 12px',
            fontSize: '11px',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          Send
        </button>
      </form>
    </div>
  );
};

export default ChatPanel;
