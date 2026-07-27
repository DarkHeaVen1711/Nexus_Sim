import React, { useMemo, useEffect, useState } from 'react';
import { CircleMarker, Popup } from 'react-leaflet';

interface ZoneMetric {
  zone_id: number;
  wait_time: number;
}

interface EquityOverlayProps {
  zoneMetrics: ZoneMetric[];
  graphData: any;
}

function waitTimeColor(wt: number, maxWt: number): string {
  if (maxWt <= 0) return '#22c55e';
  const t = Math.min(wt / maxWt, 1.0);
  if (t < 0.33) return '#22c55e';
  if (t < 0.66) return '#eab308';
  return '#ef4444';
}

export const EquityOverlay: React.FC<EquityOverlayProps> = ({ zoneMetrics, graphData }) => {
  const [centroids, setCentroids] = useState<Map<number, [number, number]>>(new Map());

  useEffect(() => {
    if (!graphData) return;
    const zoneNodes = new Map<number, { latSum: number; lonSum: number; count: number }>();
    for (const node of graphData.nodes) {
      const existing = zoneNodes.get(node.zone_id) || { latSum: 0, lonSum: 0, count: 0 };
      existing.latSum += node.lat;
      existing.lonSum += node.lon;
      existing.count++;
      zoneNodes.set(node.zone_id, existing);
    }
    const c = new Map<number, [number, number]>();
    for (const [zId, data] of zoneNodes) {
      c.set(zId, [data.latSum / data.count, data.lonSum / data.count]);
    }
    setCentroids(c);
  }, [graphData]);

  const maxWt = useMemo(() => {
    if (zoneMetrics.length === 0) return 1;
    return Math.max(...zoneMetrics.map(z => z.wait_time), 0.1);
  }, [zoneMetrics]);

  if (centroids.size === 0 || zoneMetrics.length === 0) return null;

  const wtMap = new Map(zoneMetrics.map(zm => [zm.zone_id, zm.wait_time]));

  return (
    <>
      {Array.from(centroids.entries()).map(([zoneId, [lat, lon]]) => {
        const wt = wtMap.get(zoneId) || 0;
        const color = waitTimeColor(wt, maxWt);
        const radius = Math.max(8, Math.min(25, 8 + (wt / maxWt) * 17));
        return (
          <CircleMarker
            key={`zone-${zoneId}`}
            center={[lat, lon]}
            radius={radius}
            pathOptions={{
              color: '#ffffff',
              weight: 2,
              fillColor: color,
              fillOpacity: 0.6,
            }}
          >
            <Popup>
              <div style={{ fontFamily: 'system-ui, sans-serif' }}>
                <strong>Zone {zoneId}</strong><br />
                Avg Wait: {wt.toFixed(1)}s
              </div>
            </Popup>
          </CircleMarker>
        );
      })}
    </>
  );
};
