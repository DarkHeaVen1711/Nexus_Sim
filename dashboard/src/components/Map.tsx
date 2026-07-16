import React, { useMemo, useEffect, useState } from 'react';
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { useWebSocket } from '../hooks/useWebSocket';
import { MetricsPanel } from './MetricsPanel';

// Coordinate config (Piedmont sample data)
const CITY_CENTER: [number, number] = [37.8242201, -122.247198];

export const Map: React.FC = () => {
  const { agents, metrics, zoneMetrics, isConnected, isReconnecting } = useWebSocket('ws://localhost:9002');
  const [graphData, setGraphData] = useState<any>(null);

  useEffect(() => {
    // Load sample graph to render road network
    fetch('/graph.json')
      .then(r => r.json())
      .then(data => {
        const nodeMap = new globalThis.Map();
        data.nodes.forEach((n: any) => nodeMap.set(n.id, [n.lon, n.lat]));
        
        const features = data.edges.map((e: any) => {
          const start = nodeMap.get(e.u);
          const end = nodeMap.get(e.v);
          if (!start || !end) return null;
          return {
            type: 'Feature',
            geometry: { type: 'LineString', coordinates: [start, end] },
            properties: { lanes: e.lanes, speed: e.speed_kph }
          };
        }).filter(Boolean);

        setGraphData({ type: 'FeatureCollection', features });
      })
      .catch(err => console.error('Failed to load graph.json', err));
  }, []);

  const getAgentColor = (type: number) => {
    switch (type) {
      case 0: return '#3b82f6'; // CAR
      case 1: return '#ef4444'; // BUS
      case 2: return '#eab308'; // AUTO
      case 3: return '#22c55e'; // BIKE
      case 4: return '#a855f7'; // PEDESTRIAN
      default: return '#9ca3af';
    }
  };

  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
      {isReconnecting && (
        <div className="absolute top-4 left-1/2 transform -translate-x-1/2 z-[1000] bg-yellow-500 text-white px-4 py-2 rounded shadow">
          Reconnecting to Engine...
        </div>
      )}
      
      {!isConnected && !isReconnecting && (
        <div style={{ position: 'absolute', top: '16px', left: '50%', transform: 'translateX(-50%)', zIndex: 1000, backgroundColor: '#ef4444', color: 'white', padding: '8px 16px', borderRadius: '4px', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }}>
          Disconnected
        </div>
      )}

      <MetricsPanel metrics={metrics} />

      <MapContainer 
        center={CITY_CENTER} 
        zoom={14} 
        style={{ width: '100%', height: '100%', zIndex: 1 }}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {graphData && (
          <GeoJSON 
            data={graphData} 
            style={{ color: '#4b5563', weight: 2 }} 
          />
        )}

        {agents.map(agent => (
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
              Speed/Heading: {agent.heading.toFixed(2)}
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  );
};

export default Map;
