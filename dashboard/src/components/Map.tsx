import React, { useEffect, useState, useCallback } from 'react';
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useWebSocket } from '../hooks/useWebSocket';
import { MetricsPanel } from './MetricsPanel';
import { EquityOverlay } from './EquityOverlay';
import { ViewportBoundsSender } from './ViewportBoundsSender';
import { CitySelector } from './CitySelector';
import { SimControls } from './SimControls';
import { ComparisonPanel } from './ComparisonPanel';

const CITY_CENTER: [number, number] = [37.8242201, -122.247198];

type ViewMode = 'efficiency' | 'equity';

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
  }, [map, graph]);
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
  const { agents, metrics, zoneMetrics, isConnected, isReconnecting, engineCity, engineError, engineMode, simStatus, sendMessage, sendCommand, resetState } = useWebSocket('ws://localhost:9001');
  const [graphData, setGraphData] = useState<any>(null);
  const [rawGraph, setRawGraph] = useState<any>(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [selectedCity, setSelectedCity] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('efficiency');

  // Single-simulation rule: while a city is running (or paused) the city
  // buttons are locked and switching is impossible. When the engine stops the
  // run (reset/stop) the selection clears back to the "choose a city" view.
  const simActive = simStatus === 'running' || simStatus === 'paused';
  const cityLocked = simActive;

  // Follow the engine's authoritative city (announced when it starts/loads a
  // city, or answered to the get_city probe on connect). When the engine is
  // idling it reports null and the dashboard stays on the "select a city" view.
  useEffect(() => {
    if (simStatus === 'idle' && engineCity === null) {
      setSelectedCity(null);
      setRawGraph(null);
      setGraphData(null);
      return;
    }
    if (!engineCity) return;
    if (selectedCity !== engineCity) setSelectedCity(engineCity);
  }, [simStatus, engineCity, selectedCity]);

  // Loading a new city invalidates the previous city's agents and viewport
  // bounds, so old markers and stale LOD culling never leak into the new map.
  useEffect(() => {
    resetState();
    sendMessage(JSON.stringify({ type: 'bounds', clear: true }));
  }, [selectedCity, sendMessage, resetState]);

  useEffect(() => {
    let cancelled = false;
    if (!selectedCity) {
      setGraphLoading(false);
      setRawGraph(null);
      setGraphData(null);
      return () => { cancelled = true; };
    }
    setGraphLoading(true);
    fetch(`/graphs/${selectedCity}/graph.json`)
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
  }, [selectedCity]);

  const switchCity = useCallback((city: string) => {
    if (selectedCity) return; // locked while running
    setSelectedCity(city);
    sendCommand('city', city);
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
          Open the Γÿ░ menu to start a simulation
        </div>
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

      <MetricsPanel metrics={metrics} zoneMetrics={zoneMetrics} signalMode={engineMode} />

      <ComparisonPanel />

      <MapContainer
        center={CITY_CENTER}
        zoom={14}
        style={{ width: '100%', height: '100%', zIndex: 1 }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {rawGraph && <GraphBoundsFitter graph={rawGraph} />}
        <ViewportBoundsSender sendMessage={sendMessage} />

        {graphData && (
          <GeoJSON
            data={graphData}
            interactive={false}
            style={{ color: '#4b5563', weight: 2 }}
          />
        )}

        {viewMode === 'efficiency' && agents.map(agent => (
          <CircleMarker
            key={agent.id}
            center={[agent.lat, agent.lon]}
            radius={4}
            pathOptions={{
              color: '#ffffff',
              weight: 1,
              fillColor: getAgentColor(agent.type),
              fillOpacity: 1
            }}
          >
            <Popup>
              Agent ID: {agent.id} <br />
              Type: {agent.type} <br />
              Speed: {(agent.speed * 3.6).toFixed(1)} km/h ({(agent.speed * 2.236936).toFixed(1)} mph)
            </Popup>
          </CircleMarker>
        ))}

        {viewMode === 'equity' && (
          <EquityOverlay zoneMetrics={zoneMetrics} graphData={rawGraph} />
        )}
      </MapContainer>
    </div>
  );
};

export default Map;
