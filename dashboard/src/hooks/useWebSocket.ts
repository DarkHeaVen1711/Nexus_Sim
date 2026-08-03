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
  metrics: any;
  zoneMetrics: any[];
  isConnected: boolean;
  isReconnecting: boolean;
}

const HEARTBEAT_INTERVAL_MS = 20000;
const MAX_RECONNECT_DELAY_MS = 10000;

export function useWebSocket(url: string): UseWebSocketResult {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [metrics, setMetrics] = useState<any>(null);
  const [zoneMetrics, setZoneMetrics] = useState<any[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeatRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const reconnectAttempts = useRef(0);
  const stoppedRef = useRef(false);

  const connect = useCallback(() => {
    if (stoppedRef.current) return;
    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        setIsConnected(true);
        setIsReconnecting(false);
        reconnectAttempts.current = 0;
        // Heartbeat so the server sees client activity and keeps the socket alive.
        if (heartbeatRef.current) clearInterval(heartbeatRef.current);
        heartbeatRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send('ping');
        }, HEARTBEAT_INTERVAL_MS);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(typeof event.data === 'string' ? event.data : new TextDecoder().decode(event.data));
          if (data.agents && data.metrics) {
            setAgents(data.agents);
            setMetrics(data.metrics);
            setZoneMetrics(data.zone_metrics || []);
          }
        } catch (e) {
          console.error("Failed to parse websocket message", e);
        }
      };

      ws.onclose = () => {
        if (heartbeatRef.current) {
          clearInterval(heartbeatRef.current);
          heartbeatRef.current = null;
        }
        setIsConnected(false);
        if (wsRef.current === ws) wsRef.current = null;

        if (stoppedRef.current) return;

        // Keep retrying forever with capped exponential backoff so the dashboard
        // reconnects automatically whenever the engine comes back up.
        setIsReconnecting(true);
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), MAX_RECONNECT_DELAY_MS);
        reconnectAttempts.current++;
        console.log(`WebSocket closed. Reconnecting in ${delay}ms...`);
        reconnectTimeoutRef.current = setTimeout(connect, delay);
      };

      ws.onerror = (err) => {
        console.error('WebSocket error:', err);
      };

      wsRef.current = ws;
    } catch (e) {
      console.error('Failed to create WebSocket:', e);
    }
  }, [url]);

  useEffect(() => {
    stoppedRef.current = false;
    connect();
    return () => {
      stoppedRef.current = true;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (heartbeatRef.current) clearInterval(heartbeatRef.current);
      if (wsRef.current) wsRef.current.close();
    };
  }, [connect]);

  return { agents, metrics, zoneMetrics, isConnected, isReconnecting };
}
