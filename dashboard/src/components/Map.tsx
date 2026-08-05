import React, { useEffect, useState } from 'react';
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Popup, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useWebSocket } from '../hooks/useWebSocket';
import { MetricsPanel } from './MetricsPanel';
import { EquityOverlay } from './EquityOverlay';
import { ViewportBoundsSender } from './ViewportBoundsSender';

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
  const { agents, metrics, zoneMetrics, isConnected, isReconnecting, engineCity, sendMessage } = useWebSocket('ws://localhost:9001');
  const [graphData, setGraphData] = useState<any>(null);
  const [rawGraph, setRawGraph] = useState<any>(null);
  const [graphLoading, setGraphLoading] = useState(false);
  const [selectedCity, setSelectedCity] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('efficiency');

  // Follow the engine's authoritative city (announced when it starts/loads a
  // city, or answered to the get_city probe on connect). When the engine is
  // idling it reports null and the dashboard stays on the "select a city" view.
  useEffect(() => {
    if (!engineCity) return;
    if (engineCity !== selectedCity) {
      setSelectedCity(engineCity);
    }
  }, [engineCity, selectedCity]);

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

  const toggleStyle = (active: boolean): React.CSSProperties => ({
    padding: '8px 16px',
    border: '1px solid #374151',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '13px',
    fontWeight: 600,
    fontFamily: 'system-ui, sans-serif',
    backgroundColor: active ? '#3b82f6' : 'rgba(17, 24, 39, 0.85)',
    color: active ? '#ffffff' : '#9ca3af',
    transition: 'all 0.2s',
  });

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
      {isReconnecting && (
        <div style={{ position: 'absolute', top: '16px', left: '50%', transform: 'translateX(-50%)', zIndex: 1000, backgroundColor: '#eab308', color: '#000', padding: '8px 16px', borderRadius: '6px', fontWeight: 600 }}>
          Reconnecting to Engine...
        </div>
      )}

      {!isConnected && !isReconnecting && (
        <div style={{ position: 'absolute', top: '16px', left: '50%', transform: 'translateX(-50%)', zIndex: 1000, backgroundColor: '#ef4444', color: 'white', padding: '8px 16px', borderRadius: '6px' }}>
          Disconnected
        </div>
      )}

      {selectedCity && graphLoading && (
        <div style={{ position: 'absolute', bottom: '24px', left: '50%', transform: 'translateX(-50%)', zIndex: 1000, backgroundColor: 'rgba(17, 24, 39, 0.9)', color: '#e5e7eb', padding: '8px 16px', borderRadius: '6px', border: '1px solid #374151' }}>
          Loading {selectedCity} road network...
        </div>
      )}

      <div style={{ position: 'absolute', top: '20px', left: '20px', zIndex: 1000, display: 'flex', gap: '4px', backgroundColor: 'rgba(17, 24, 39, 0.9)', padding: '4px', borderRadius: '8px', border: '1px solid #374151' }}>
        <button style={toggleStyle(viewMode === 'efficiency')} onClick={() => setViewMode('efficiency')}>
          Efficiency
        </button>
        <button style={toggleStyle(viewMode === 'equity')} onClick={() => setViewMode('equity')}>
          Equity
        </button>
      </div>

      <MetricsPanel metrics={metrics} zoneMetrics={zoneMetrics} />

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
