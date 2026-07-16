import { useState, useEffect, useRef, useCallback } from 'react';

// Assuming we have the generated FlatBuffer classes available:
// import { Frame } from '../schemas/agent_delta_generated';

export interface Agent {
  id: number;
  lat: number;
  lon: number;
  heading: number;
  type: number;
}

interface UseWebSocketResult {
  agents: Agent[];
  isConnected: boolean;
  isReconnecting: boolean;
}

export function useWebSocket(url: string): UseWebSocketResult {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const reconnectAttempts = useRef(0);
  const MAX_RETRIES = 5;

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url);
      ws.binaryType = 'arraybuffer';

      ws.onopen = () => {
        setIsConnected(true);
        setIsReconnecting(false);
        reconnectAttempts.current = 0;
        console.log('WebSocket connected');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setAgents(data);
        } catch (e) {
          console.error("Failed to parse websocket message", e);
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        wsRef.current = null;
        
        if (reconnectAttempts.current < MAX_RETRIES) {
          setIsReconnecting(true);
          const timeout = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000);
          console.log(`WebSocket closed. Reconnecting in ${timeout}ms...`);
          reconnectTimeoutRef.current = setTimeout(connect, timeout);
          reconnectAttempts.current++;
        } else {
          setIsReconnecting(false);
          console.error('WebSocket connection lost permanently.');
        }
      };

      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        ws.close();
      };

      wsRef.current = ws;
    } catch (e) {
      console.error('Failed to create WebSocket:', e);
    }
  }, [url]);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  return { agents, isConnected, isReconnecting };
}
