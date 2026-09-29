/**
 * NexusSim Unified Network Configuration
 *
 * Frontend Port: 3000 (React Dashboard)
 * Backend Port:  8000 (Unified API Gateway)
 */

export const FRONTEND_PORT = 3000;
export const BACKEND_PORT = 8000;

export const BACKEND_HTTP = `http://localhost:${BACKEND_PORT}`;
export const BACKEND_WS = `ws://localhost:${BACKEND_PORT}`;

export const ENDPOINTS = {
  /** C++ Simulation Engine WebSocket stream (via Gateway) */
  ENGINE_WS: `${BACKEND_WS}/ws`,

  /** Synthetic Virtual Camera frame and blob telemetry */
  CAMERA_FEED: `${BACKEND_HTTP}/api/camera/feed`,

  /** NLP Contextual Q&A Chat endpoint */
  CHAT: `${BACKEND_HTTP}/api/chat`,

  /** Incident Injection & Fuzzy Gazetteer */
  INCIDENT: `${BACKEND_HTTP}/api/incident`,

  /** Cross-Subject Event Bus WebSocket stream */
  EVENTS_WS: `${BACKEND_WS}/ws/events`,

  /** 36-Algorithm Master Catalog REST endpoint */
  ALGO_CATALOG: `${BACKEND_HTTP}/api/algo`,

  /** Gateway Health & Microservices status */
  HEALTH: `${BACKEND_HTTP}/api/health`,
};
