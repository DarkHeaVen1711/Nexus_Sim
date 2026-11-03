import React from 'react';

export interface StationData {
  node_id: number;
  name: string;
  total_stalls: number;
  occupied_stalls: number;
  charge_rate_kw: number;
}

interface ChargingStationOverlayProps {
  stations: StationData[];
  onSelectStation?: (node_id: number) => void;
}

export const ChargingStationOverlay: React.FC<ChargingStationOverlayProps> = ({
  stations,
  onSelectStation,
}) => {
  if (!stations || stations.length === 0) return null;

  return (
    <div className="absolute top-20 right-4 z-40 bg-gray-900/90 text-white p-3.5 rounded-xl border border-cyan-500/40 shadow-2xl backdrop-blur-md w-72 text-xs">
      <div className="flex items-center justify-between border-b border-gray-800 pb-2 mb-2.5">
        <span className="font-semibold text-cyan-400 flex items-center gap-1.5">
          ⚡ EV Charging Infrastructure
        </span>
        <span className="text-[10px] text-gray-400">{stations.length} Hubs</span>
      </div>

      <div className="space-y-2 max-h-56 overflow-y-auto pr-1">
        {stations.map((st) => {
          const occupancyPct = Math.round((st.occupied_stalls / st.total_stalls) * 100);
          const isFull = st.occupied_stalls >= st.total_stalls;

          return (
            <div
              key={st.node_id}
              onClick={() => onSelectStation && onSelectStation(st.node_id)}
              className="p-2 bg-gray-800/60 hover:bg-gray-800 rounded-lg cursor-pointer transition border border-gray-700/50"
            >
              <div className="flex justify-between items-center mb-1">
                <span className="font-medium text-gray-200">{st.name}</span>
                <span className="text-[10px] text-cyan-400 font-mono">{st.charge_rate_kw} kW</span>
              </div>
              <div className="flex justify-between items-center text-[11px] text-gray-400 mb-1.5">
                <span>Stalls: {st.occupied_stalls} / {st.total_stalls}</span>
                <span className={isFull ? 'text-red-400 font-semibold' : 'text-emerald-400'}>
                  {isFull ? 'FULL' : `${occupancyPct}% Busy`}
                </span>
              </div>
              <div className="w-full bg-gray-700 h-1.5 rounded-full overflow-hidden">
                <div
                  className={`h-full transition-all duration-300 ${
                    isFull ? 'bg-red-500' : occupancyPct > 60 ? 'bg-amber-400' : 'bg-cyan-400'
                  }`}
                  style={{ width: `${occupancyPct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
