import React, { useEffect, useState, useCallback, useRef, useMemo } from 'react';
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Popup, Polyline, useMap, useMapEvents, ZoomControl } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { useWebSocket } from '../hooks/useWebSocket';
import { EquityOverlay } from './EquityOverlay';
import { ViewportBoundsSender } from './ViewportBoundsSender';
import { CitySelector } from './CitySelector';
import { SimControls } from './SimControls';
import { RightDock } from './RightDock';
import { NLPCommandConsole } from './NLPCommandConsole';

const CITY_CENTER: [number, number] = [37.8242201, -122.247198];

type ViewMode = 'efficiency' | 'equity';
type PathMode = 'all' | 'selected' | 'trails' | 'none';

// Fit the map to the loaded graph's bounding box once so the viewport matches
// the city the engine is simulating (keeps LOD bounds meaningful out of the box).
const GraphBoundsFitter: React.FC<{ graph: any }> = ({ graph }) => {
  const map = useMap();
  useEffect(() => {
    if (!graph?.nodes?.length) return;
    const lats = graph.nodes.map((n: any) => n.lat);
    const lons = graph.nodes.map((n: any) => n.lon);
    const southWest = [Math.min(...lats), Math.min(...lons)] as [number, number];
    const northEast = [Math.max(...lats), Math.max(...lons)] as [number, number];
    map.fitBounds([southWest, northEast]);
    setTimeout(() => {
      map.invalidateSize();
    }, 100);
  }, [map, graph]);
  return null;
};

// Deselect active agent when clicking empty map space
const MapClickHandler: React.FC<{ onDeselect: () => void }> = ({ onDeselect }) => {
  useMapEvents({
    click: () => onDeselect(),
  });
  return null;
};

// Collapse the whole road network into a single MultiLineString feature so
// large cities (chicago has ~77k edges) stay renderable in the browser.
const buildGraphFeature = (data: any): any => {
  const nodeMap = new globalThis.Map();
  data.nodes.forEach((n: any) => nodeMap.set(n.id, [n.lon, n.lat]));
  const coords: number[][][] = [];
  data.edges.forEach((e: any) => {
    const start = nodeMap.get(e.u);
    const end = nodeMap.get(e.v);
    if (!start || !end) return;
    coords.push([start, end]);
  });
  return {
    type: 'FeatureCollection',
    features: [
      {
        type: 'Feature',
        geometry: { type: 'MultiLineString', coordinates: coords },
        properties: {},
      },
    ],
  };
};

export const Map: React.FC = () => {
  const { agents, metrics, zoneMetrics, signals, isConnected, isReconnecting, engineCity, engineError, engineMode, simStatus, sendMessage, sendCommand, sendPolicySwitch, resetState } = useWebSocket('ws://localhost:9001');
  const [graphData, setGraphData] = useState<any>(null);
  const [rawGraph, setRawGraph] = useState<any>(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [selectedCity, setSelectedCity] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('efficiency');
  const [pathMode, setPathMode] = useState<PathMode>('all');
  const [selectedAgentId, setSelectedAgentId] = useState<number | null>(null);
  const [isDockCollapsed, setIsDockCollapsed] = useState(false);
  const prevCityRef = useRef<string | null>(null);
  const trailsRef = useRef<globalThis.Map<number, [number, number][]>>(new globalThis.Map());

  // Fast node lookup map: nodeId -> [lat, lon]
  const nodeMap = useMemo(() => {
    if (!rawGraph?.nodes) return new globalThis.Map<number, [number, number]>();
    const map = new globalThis.Map<number, [number, number]>();
    for (const n of rawGraph.nodes) {
      map.set(n.id, [n.lat, n.lon]);
    }
    return map;
  }, [rawGraph]);

  // Selected agent details
  const selectedAgent = useMemo(() => {
    if (selectedAgentId === null) return null;
    return agents.find(a => a.id === selectedAgentId) ?? null;
  }, [agents, selectedAgentId]);

  // Full planned route for selected agent
  const selectedFullPath = useMemo(() => {
    if (!selectedAgent?.path || !nodeMap.size) return [];
    const pts: [number, number][] = [];
    for (const id of selectedAgent.path) {
      const pt = nodeMap.get(id);
      if (pt) pts.push(pt);
    }
    return pts;
  }, [selectedAgent, nodeMap]);

  // Remaining active path for selected agent (from live position to destination)
  const selectedRemainingPath = useMemo(() => {
    if (!selectedAgent?.path || !nodeMap.size) return [];
    const edgeIdx = Math.max(0, selectedAgent.edge_idx ?? 0);
    const pts: [number, number][] = [[selectedAgent.lat, selectedAgent.lon]];
    for (let k = edgeIdx + 1; k < selectedAgent.path.length; ++k) {
      const pt = nodeMap.get(selectedAgent.path[k]);
      if (pt) pts.push(pt);
    }
    return pts;
  }, [selectedAgent, nodeMap]);

  const selectedOriginCoord = useMemo(() => {
    if (selectedAgent?.origin === undefined || selectedAgent?.origin === null || !nodeMap.size) return null;
    return nodeMap.get(selectedAgent.origin) ?? null;
  }, [selectedAgent, nodeMap]);

  const selectedDestCoord = useMemo(() => {
    if (selectedAgent?.destination === undefined || selectedAgent?.destination === null || !nodeMap.size) return null;
    return nodeMap.get(selectedAgent.destination) ?? null;
  }, [selectedAgent, nodeMap]);

  // Record movement trails for active agents
  useEffect(() => {
    if (pathMode !== 'trails' && pathMode !== 'all') return;
    agents.forEach(agent => {
      const t = trailsRef.current.get(agent.id) || [];
      const last = t[t.length - 1];
      if (!last || Math.abs(last[0] - agent.lat) > 0.00002 || Math.abs(last[1] - agent.lon) > 0.00002) {
        t.push([agent.lat, agent.lon]);
        if (t.length > 8) t.shift();
        trailsRef.current.set(agent.id, t);
      }
    });
  }, [agents, pathMode]);

  // Single-simulation rule: while a city is running (or paused) the city
  // buttons are locked and switching is impossible. When the engine stops the
  // run (reset/stop) the selection clears back to the "choose a city" view.
  const simActive = simStatus === 'running' || simStatus === 'paused';
  const cityLocked = simActive;

  // Follow the engine's authoritative city (announced on startup or city switch).
  useEffect(() => {
    if (engineCity !== undefined && engineCity !== selectedCity) {
      setSelectedCity(engineCity);
    }
  }, [engineCity, selectedCity]);

  // Loading a new city invalidates the previous city's agents and viewport
  // bounds, so old markers and stale LOD culling never leak into the new map.
  useEffect(() => {
    if (prevCityRef.current === selectedCity) return;
    prevCityRef.current = selectedCity;

    resetState();
    setSelectedAgentId(null);
    trailsRef.current.clear();
    sendMessage(JSON.stringify({ type: 'bounds', clear: true }));

    let cancelled = false;
    if (!selectedCity) {
      setGraphLoading(false);
      setRawGraph(null);
      setGraphData(null);
      return () => { cancelled = true; };
    }

    setGraphLoading(true);
    const cityKey = selectedCity.toLowerCase();
    fetch(`/graphs/${cityKey}/graph.json`)
      .then(r => {
        if (!r.ok) throw new Error(`Failed to load graph for ${selectedCity}`);
        return r.json();
      })
      .then(data => {
        if (cancelled) return;
        setRawGraph(data);
        setGraphData(buildGraphFeature(data));
      })
      .catch(err => {
        console.error('Failed to load graph', err);
        if (cancelled) return;
        setRawGraph(null);
        setGraphData(null);
      })
      .finally(() => {
        if (!cancelled) setGraphLoading(false);
      });

    return () => { cancelled = true; };
  }, [selectedCity, sendMessage, resetState]);

  const switchCity = useCallback((city: string) => {
    const target = city.toLowerCase();
    if (target === selectedCity?.toLowerCase()) return;
    setSelectedCity(target);
    sendCommand('city', target);
  }, [selectedCity, sendCommand]);

  const getAgentColor = (type: number) => {
    switch (type) {
      case 0: return '#3b82f6';
      case 1: return '#ef4444';
      case 2: return '#eab308';
      case 3: return '#22c55e';
      case 4: return '#a855f7';
      default: return '#9ca3af';
    }
  };

  const getAgentTypeName = (type: number) => {
    switch (type) {
      case 0: return 'Car';
      case 1: return 'Bus';
      case 2: return 'Auto-rickshaw';
      case 3: return 'Two-wheeler';
      case 4: return 'Pedestrian';
      default: return 'Vehicle';
    }
  };

  const handlePause = () => sendCommand('pause');
  const handleResume = () => sendCommand('resume');
  const handleRestart = () => sendCommand('restart');
  const handleReset = () => sendCommand('reset');

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
      {isReconnecting && (
        <div style={{ position: 'absolute', top: '68px', left: '50%', transform: 'translateX(-50%)', zIndex: 1000, backgroundColor: '#eab308', color: '#000', padding: '8px 16px', borderRadius: '6px', fontWeight: 600 }}>
          Reconnecting to Engine...
        </div>
      )}

      {!isConnected && !isReconnecting && (
        <div style={{ position: 'absolute', top: '68px', left: '50%', transform: 'translateX(-50%)', zIndex: 1000, backgroundColor: '#ef4444', color: 'white', padding: '8px 16px', borderRadius: '6px' }}>
          Disconnected
        </div>
      )}

      {engineError && (
        <div style={{ position: 'absolute', top: '68px', left: '50%', transform: 'translateX(-50%)', zIndex: 1000, backgroundColor: '#ef4444', color: 'white', padding: '8px 16px', borderRadius: '6px' }}>
          {engineError}
        </div>
      )}

      {selectedCity && graphLoading && (
        <div style={{ position: 'absolute', bottom: '24px', left: '50%', transform: 'translateX(-50%)', zIndex: 1000, backgroundColor: 'rgba(17, 24, 39, 0.9)', color: '#e5e7eb', padding: '8px 16px', borderRadius: '6px', border: '1px solid #374151' }}>
          Loading {selectedCity} road network...
        </div>
      )}

      {!selectedCity && isConnected && (
        <div style={{ position: 'absolute', bottom: '24px', left: '50%', transform: 'translateX(-50%)', zIndex: 1000, backgroundColor: 'rgba(17, 24, 39, 0.9)', color: '#e5e7eb', padding: '10px 18px', borderRadius: '8px', border: '1px solid #374151', fontSize: '14px', fontWeight: 600 }}>
          Open the ☰ menu to start a simulation
        </div>
      )}

      {isConnected && (
        <NLPCommandConsole
          onSendMessage={sendMessage}
          simStatus={simStatus}
          dockState={
            !(metrics || simActive)
              ? 'none'
              : isDockCollapsed
                ? 'collapsed'
                : 'expanded'
          }
        />
      )}

      <CitySelector
        activeCity={selectedCity}
        disabled={graphLoading}
        locked={cityLocked}
        locale="en"
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        onSelect={switchCity}
      />

      {/* Path Mode Segmented Control */}
      <div
        style={{
          position: 'absolute',
          top: '20px',
          left: '74px',
          zIndex: 1100,
          display: 'flex',
          alignItems: 'center',
          gap: '4px',
          backgroundColor: 'rgba(17, 24, 39, 0.92)',
          backdropFilter: 'blur(8px)',
          border: '1px solid #374151',
          borderRadius: '8px',
          padding: '4px 6px',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.2)',
        }}
      >
        <span style={{ fontSize: '11px', fontWeight: 600, color: '#9ca3af', padding: '0 6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Paths:
        </span>
        {(['all', 'selected', 'trails', 'none'] as const).map(mode => {
          const active = pathMode === mode;
          const labels = {
            all: 'All Routes',
            selected: 'Selected',
            trails: 'Trails',
            none: 'Off',
          };
          return (
            <button
              key={mode}
              onClick={() => setPathMode(mode)}
              style={{
                background: active ? '#2563eb' : 'transparent',
                color: active ? '#ffffff' : '#9ca3af',
                border: 'none',
                borderRadius: '5px',
                padding: '5px 9px',
                fontSize: '12px',
                fontWeight: active ? 600 : 500,
                cursor: 'pointer',
                transition: 'all 0.15s ease',
              }}
            >
              {labels[mode]}
            </button>
          );
        })}
      </div>

      {/* Selected Agent Inspector HUD */}
      {selectedAgent && (
        <div
          style={{
            position: 'absolute',
            bottom: '24px',
            left: '24px',
            zIndex: 1100,
            backgroundColor: 'rgba(17, 24, 39, 0.95)',
            backdropFilter: 'blur(10px)',
            border: '1px solid #06b6d4',
            borderRadius: '10px',
            padding: '14px 16px',
            color: '#f3f4f6',
            minWidth: '260px',
            boxShadow: '0 10px 25px -5px rgba(0, 229, 255, 0.25)',
            fontFamily: 'system-ui, sans-serif',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span
                style={{
                  display: 'inline-block',
                  width: '10px',
                  height: '10px',
                  borderRadius: '50%',
                  backgroundColor: getAgentColor(selectedAgent.type),
                  boxShadow: `0 0 8px ${getAgentColor(selectedAgent.type)}`,
                }}
              />
              <span style={{ fontWeight: 700, fontSize: '14px', color: '#ffffff' }}>
                {getAgentTypeName(selectedAgent.type)} #{selectedAgent.id}
              </span>
            </div>
            <button
              onClick={() => setSelectedAgentId(null)}
              style={{
                background: 'transparent',
                border: 'none',
                color: '#9ca3af',
                fontSize: '16px',
                cursor: 'pointer',
                padding: '0 4px',
                lineHeight: 1,
              }}
              title="Close inspection"
            >
              ✕
            </button>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '12px' }}>
            <div style={{ backgroundColor: 'rgba(31, 41, 55, 0.6)', padding: '6px 8px', borderRadius: '6px' }}>
              <div style={{ color: '#9ca3af', fontSize: '10px', textTransform: 'uppercase' }}>Speed</div>
              <div style={{ fontWeight: 600, color: '#38bdf8' }}>
                {(selectedAgent.speed * 3.6).toFixed(1)} km/h
              </div>
            </div>
            <div style={{ backgroundColor: 'rgba(31, 41, 55, 0.6)', padding: '6px 8px', borderRadius: '6px' }}>
              <div style={{ color: '#9ca3af', fontSize: '10px', textTransform: 'uppercase' }}>Route Progress</div>
              <div style={{ fontWeight: 600, color: '#34d399' }}>
                {selectedAgent.path?.length
                  ? `${Math.round(((selectedAgent.edge_idx ?? 0) / Math.max(1, selectedAgent.path.length - 1)) * 100)}% (Leg ${(selectedAgent.edge_idx ?? 0) + 1}/${selectedAgent.path.length})`
                  : 'Active'}
              </div>
            </div>
          </div>

          {selectedAgent.origin !== undefined && selectedAgent.destination !== undefined && (
            <div style={{ marginTop: '8px', fontSize: '11px', color: '#9ca3af', display: 'flex', justifyContent: 'space-between', borderTop: '1px solid #374151', paddingTop: '6px' }}>
              <span>From: Node {selectedAgent.origin}</span>
              <span>To: Node {selectedAgent.destination}</span>
            </div>
          )}
        </div>
      )}

      {selectedCity && (
        <SimControls
          status={simStatus}
          city={selectedCity}
          disabled={graphLoading}
          onPause={handlePause}
          onResume={handleResume}
          onRestart={handleRestart}
          onReset={handleReset}
        />
      )}

      <RightDock
        metrics={metrics}
        zoneMetrics={zoneMetrics}
        signalMode={engineMode}
        connected={isConnected}
        simActive={simActive}
        onSwitch={sendPolicySwitch}
        signals={signals}
        onSwitchPolicy={sendPolicySwitch}
        city={engineCity || selectedCity || 'chicago'}
        collapsed={isDockCollapsed}
        onToggleCollapse={() => setIsDockCollapsed((c) => !c)}
      />

      <MapContainer
        center={CITY_CENTER}
        zoom={14}
        zoomControl={false}
        style={{ width: '100%', height: '100%', zIndex: 1 }}
      >
        <ZoomControl position="bottomleft" />
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {rawGraph && <GraphBoundsFitter graph={rawGraph} />}
        <MapClickHandler onDeselect={() => setSelectedAgentId(null)} />
        <ViewportBoundsSender sendMessage={sendMessage} />

        {graphData && (
          <GeoJSON
            data={graphData}
            interactive={false}
            style={{ color: '#4b5563', weight: 2 }}
          />
        )}

        {/* Global Agent Routes when pathMode === 'all' */}
        {viewMode === 'efficiency' && pathMode === 'all' && agents.slice(0, 150).map(agent => {
          if (!agent.path || agent.path.length < 2 || agent.id === selectedAgentId) return null;
          const edgeIdx = Math.max(0, agent.edge_idx ?? 0);
          const pts: [number, number][] = [[agent.lat, agent.lon]];
          for (let k = edgeIdx + 1; k < agent.path.length; ++k) {
            const pt = nodeMap.get(agent.path[k]);
            if (pt) pts.push(pt);
          }
          if (pts.length < 2) return null;
          return (
            <Polyline
              key={`path-${agent.id}`}
              positions={pts}
              interactive={false}
              pathOptions={{
                color: getAgentColor(agent.type),
                weight: 2,
                opacity: 0.55,
                lineCap: 'round',
                lineJoin: 'round',
              }}
            />
          );
        })}

        {/* Dynamic Movement Trails when pathMode === 'trails' */}
        {viewMode === 'efficiency' && pathMode === 'trails' && agents.map(agent => {
          const trail = trailsRef.current.get(agent.id);
          if (!trail || trail.length < 2) return null;
          return (
            <Polyline
              key={`trail-${agent.id}`}
              positions={trail}
              interactive={false}
              pathOptions={{
                color: getAgentColor(agent.type),
                weight: 3,
                opacity: 0.7,
                lineCap: 'round',
              }}
            />
          );
        })}

        {/* Selected Agent Route Highlights */}
        {viewMode === 'efficiency' && (pathMode === 'all' || pathMode === 'selected') && selectedAgent && (
          <>
            {/* Planned Route Line */}
            {selectedFullPath.length > 1 && (
              <Polyline
                positions={selectedFullPath}
                interactive={false}
                pathOptions={{
                  color: '#0891b2',
                  weight: 4,
                  opacity: 0.65,
                  dashArray: '5, 8',
                }}
              />
            )}

            {/* Remaining Route Ahead */}
            {selectedRemainingPath.length > 1 && (
              <Polyline
                positions={selectedRemainingPath}
                interactive={false}
                pathOptions={{
                  color: '#06b6d4',
                  weight: 5,
                  opacity: 0.95,
                  lineCap: 'round',
                }}
              />
            )}

            {/* Origin Pin */}
            {selectedOriginCoord && (
              <CircleMarker
                center={selectedOriginCoord}
                radius={7}
                pathOptions={{
                  color: '#ffffff',
                  fillColor: '#10b981',
                  fillOpacity: 1,
                  weight: 2,
                }}
              >
                <Popup>
                  <strong>Trip Origin</strong><br />
                  Node: {selectedAgent.origin}
                </Popup>
              </CircleMarker>
            )}

            {/* Destination Pin */}
            {selectedDestCoord && (
              <CircleMarker
                center={selectedDestCoord}
                radius={8}
                pathOptions={{
                  color: '#ffffff',
                  fillColor: '#ef4444',
                  fillOpacity: 1,
                  weight: 2,
                }}
              >
                <Popup>
                  <strong>Trip Destination</strong><br />
                  Node: {selectedAgent.destination}
                </Popup>
              </CircleMarker>
            )}
          </>
        )}

        {/* Agent Markers */}
        {viewMode === 'efficiency' && agents.map(agent => {
          const isSelected = agent.id === selectedAgentId;
          return (
            <CircleMarker
              key={agent.id}
              center={[agent.lat, agent.lon]}
              radius={isSelected ? 7 : 4}
              pathOptions={{
                color: isSelected ? '#00ffff' : '#ffffff',
                weight: isSelected ? 2.5 : 1,
                fillColor: getAgentColor(agent.type),
                fillOpacity: 1,
                bubblingMouseEvents: false,
              }}
              eventHandlers={{
                click: (e) => {
                  if (e.originalEvent) {
                    e.originalEvent.stopPropagation();
                  }
                  L.DomEvent.stopPropagation(e as any);
                  setSelectedAgentId(agent.id);
                },
              }}
            >
              <Popup>
                <div style={{ fontSize: '13px', lineHeight: 1.4 }}>
                  <strong>{getAgentTypeName(agent.type)} #{agent.id}</strong><br />
                  Speed: {(agent.speed * 3.6).toFixed(1)} km/h ({(agent.speed * 2.236936).toFixed(1)} mph)<br />
                  {agent.path?.length ? (
                    <span>
                      Route: {agent.path.length} nodes ({(agent.edge_idx ?? 0) + 1}/{agent.path.length})<br />
                    </span>
                  ) : null}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setSelectedAgentId(agent.id);
                    }}
                    style={{
                      marginTop: '6px',
                      padding: '3px 8px',
                      backgroundColor: '#2563eb',
                      color: 'white',
                      border: 'none',
                      borderRadius: '4px',
                      cursor: 'pointer',
                      fontSize: '11px',
                    }}
                  >
                    Highlight Route
                  </button>
                </div>
              </Popup>
            </CircleMarker>
          );
        })}

        {viewMode === 'equity' && (
          <EquityOverlay zoneMetrics={zoneMetrics} graphData={rawGraph} />
        )}
      </MapContainer>
    </div>
  );
};

export default Map;
