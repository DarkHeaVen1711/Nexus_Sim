import React from 'react';

interface GreenWaveCorridorProps {
  activeCorridorNodes: number[];
  preemptionDurationRemaining: number;
  vehicleSpeedKmh: number;
  onClearPreemption?: () => void;
}

export const GreenWaveCorridor: React.FC<GreenWaveCorridorProps> = ({
  activeCorridorNodes,
  preemptionDurationRemaining,
  vehicleSpeedKmh,
  onClearPreemption,
}) => {
  if (activeCorridorNodes.length === 0) return null;

  return (
    <div className="absolute bottom-16 left-6 z-40 bg-gray-950/90 text-white p-3.5 rounded-xl border border-emerald-500/50 shadow-2xl backdrop-blur-md w-72 text-xs">
      <div className="flex items-center justify-between border-b border-gray-800 pb-2 mb-2">
        <span className="font-semibold text-emerald-400 flex items-center gap-1.5">
          🟢 Emergency Green Wave Active
        </span>
        <span className="animate-pulse w-2 h-2 rounded-full bg-emerald-400"></span>
      </div>

      <div className="space-y-1.5 text-gray-300">
        <div className="flex justify-between">
          <span className="text-gray-400">Preemption Hold:</span>
          <span className="font-mono text-emerald-300">{preemptionDurationRemaining.toFixed(1)}s</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Intersections Locked:</span>
          <span className="font-mono">{activeCorridorNodes.length}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-400">Speed:</span>
          <span className="font-mono">{vehicleSpeedKmh.toFixed(0)} km/h</span>
        </div>
      </div>

      <div className="mt-3 flex gap-1 items-center overflow-x-auto py-1">
        {activeCorridorNodes.map((node, i) => (
          <React.Fragment key={node}>
            <span className="px-1.5 py-0.5 bg-emerald-900/60 border border-emerald-500/40 rounded text-[10px] font-mono text-emerald-200">
              #{node}
            </span>
            {i < activeCorridorNodes.length - 1 && <span className="text-emerald-500 text-[10px]">→</span>}
          </React.Fragment>
        ))}
      </div>

      {onClearPreemption && (
        <button
          onClick={onClearPreemption}
          className="mt-3 w-full py-1 bg-gray-800 hover:bg-gray-700 text-gray-300 rounded text-[11px] font-medium transition"
        >
          Cancel Preemption & Resume Cycle
        </button>
      )}
    </div>
  );
};
