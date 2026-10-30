/**
 * NexusSim Unified Network Configuration
 *
 * Frontend Port: 3000 (React Dashboard)
 * Backend Port:  8000 (Unified API Gateway)
 */

export const FRONTEND_PORT = 3000;
export const BACKEND_PORT = 8000;

const isBrowser = typeof window !== 'undefined';
const wsProto = isBrowser && window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const host = isBrowser ? window.location.host : `localhost:${FRONTEND_PORT}`;

export const BACKEND_HTTP = isBrowser ? '' : `https://localhost:${BACKEND_PORT}`;
export const BACKEND_WS = isBrowser ? `${wsProto}//${host}` : `wss://localhost:${BACKEND_PORT}`;

export const ENDPOINTS = {
  /** Gateway base HTTP URL */
  GATEWAY_URL: BACKEND_HTTP,

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

  /** 48-Algorithm Master Catalog REST endpoint (legacy 36_algo_matrix.json path) */
  ALGO_CATALOG: `${BACKEND_HTTP}/api/algo`,

  /** Gateway Health & Microservices status */
  HEALTH: `${BACKEND_HTTP}/api/health`,

  /** Dynamic city list (multi-tenant onboarding) */
  CITIES: `${BACKEND_HTTP}/api/cities`,

  /** Public emissions estimate (pure computation) */
  EMISSIONS_ESTIMATE: `${BACKEND_HTTP}/api/emissions/estimate`,

  /** NexusTwin Ingestion Endpoints */
  TWIN_SEARCH: `${BACKEND_HTTP}/api/v1/twin/search`,
  TWIN_UPLOAD: `${BACKEND_HTTP}/api/v1/twin/upload`,
  TWIN_PROGRESS: `${BACKEND_HTTP}/api/v1/twin/progress`,
  TWIN_CITIES: `${BACKEND_HTTP}/api/v1/twin/cities`,
};
