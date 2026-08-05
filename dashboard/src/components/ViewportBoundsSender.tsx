import { useEffect } from 'react';
import { useMap, useMapEvents } from 'react-leaflet';

interface Props {
  sendMessage: (data: string) => void;
}

// Phase 4.3 LOD culling: whenever the viewport changes, tell the engine the
// current bounds so it only broadcasts agents inside them.
export const ViewportBoundsSender: React.FC<Props> = ({ sendMessage }) => {
  const map = useMap();

  const sendBounds = () => {
    const b = map.getBounds();
    const msg = {
      type: 'bounds',
      min_lat: b.getSouthWest().lat,
      min_lon: b.getSouthWest().lng,
      max_lat: b.getNorthEast().lat,
      max_lon: b.getNorthEast().lng,
    };
    sendMessage(JSON.stringify(msg));
  };

  useMapEvents({
    moveend: sendBounds,
    zoomend: sendBounds,
  });

  useEffect(() => {
    sendBounds();
  });

  return null;
};
