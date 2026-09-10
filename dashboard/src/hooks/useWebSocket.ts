import { useState, useEffect, useRef, useCallback } from 'react';

// Assuming we have the generated FlatBuffer classes available:
// import { Frame } from '../schemas/agent_delta_generated';

export interface Agent {
  id: number;
  lat: number;
  lon: number;
  heading: number;
  type: number;
  speed: number;
}

interface UseWebSocketResult {
  agents: Agent[];
  metrics: any;
  zoneMetrics: any[];
  isConnected: boolean;
  isReconnecting: boolean;
  engineCity: string | null;
  engineError: string | null;
  engineMode: 'ai' | 'webster' | null;
  simStatus: 'idle' | 'running' | 'paused' | null;
  sendMessage: (data: string) => void;
  sendCommand: (command: string, value?: string) => void;
  resetState: () => void;
}

const HEARTBEAT_INTERVAL_MS = 20000;
const MAX_RECONNECT_DELAY_MS = 10000;

export function useWebSocket(url: string): UseWebSocketResult {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [metrics, setMetrics] = useState<any>(null);
  const [zoneMetrics, setZoneMetrics] = useState<any[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [isReconnecting, setIsReconnecting] = useState(false);
  const [engineCity, setEngineCity] = useState<string | null>(null);
  const [engineError, setEngineError] = useState<string | null>(null);
  // Phase 8.7: signal control mode reported by the engine ("ai" when a
  // policy is loaded, "webster" for the fixed-time baseline).
  const [engineMode, setEngineMode] = useState<'ai' | 'webster' | null>(null);
  // Lifecycle of the engine's simulation: requested by the dashboard, mirrored
  // by the engine's paused/resumed/stopped + city_loaded broadcasts. null until
  // the first message from the engine tells us where things stand.
  const [simStatus, setSimStatus] = useState<'idle' | 'running' | 'paused' | null>(null);

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
        // Clear stale data from a previous connection so the dashboard doesn't
        // flash old agents/metrics briefly after a reconnect.
        setAgents([]);
        setMetrics(null);
        setZoneMetrics([]);
        setEngineError(null);
        setSimStatus(null);
        // Ask which city the engine is simulating in case we connected after
        // its startup announcement (or the engine was started with --city).
        ws.send(JSON.stringify({ type: 'get_city' }));
        // Heartbeat so the server sees client activity and keeps the socket alive.
        // The server replies with "pong", which also resets its idle-timeout.
        if (heartbeatRef.current) clearInterval(heartbeatRef.current);
        heartbeatRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) ws.send('ping');
        }, HEARTBEAT_INTERVAL_MS);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(typeof event.data === 'string' ? event.data : new TextDecoder().decode(event.data));
          if (data.type === 'city_loaded') {
            setEngineCity(data.city);
            setEngineError(null);
            setSimStatus(data.city ? 'running' : 'idle');
            return;
          }
          if (data.type === 'paused') {
            setSimStatus('paused');
            return;
          }
          if (data.type === 'resumed') {
            setSimStatus('running');
            return;
          }
          if (data.type === 'stopped') {
            setSimStatus('idle');
            return;
          }
          if (data.type === 'error') {
            setEngineError(data.message || 'Engine error');
            return;
          }
          if (data.agents && data.metrics) {
            setAgents(data.agents);
            setMetrics(data.metrics);
            setZoneMetrics(data.zone_metrics || []);
            if (data.city) setEngineCity(data.city);
            if (data.metrics.signal_mode === 'ai'
                || data.metrics.signal_mode === 'webster') {
              setEngineMode(data.metrics.signal_mode);
            }
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

  const sendMessage = useCallback((data: string) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(data);
  }, []);

  // Typed convenience for the dashboard's simulation controls. sendMessage
  // (data type field only) is required by the {type, city} shape.
  const sendCommand = useCallback((command: string, value?: string) => {
    sendMessage(value ? JSON.stringify({ type: command, city: value })
                       : JSON.stringify({ type: command }));
  }, [sendMessage]);

  const resetState = useCallback(() => {
    setAgents([]);
    setMetrics(null);
    setZoneMetrics([]);
    setEngineError(null);
    setSimStatus(null);
  }, []);

  return { agents, metrics, zoneMetrics, isConnected, isReconnecting, engineCity, engineError, engineMode, simStatus, sendMessage, sendCommand, resetState };
}
