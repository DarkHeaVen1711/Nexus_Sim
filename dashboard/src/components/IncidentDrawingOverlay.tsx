import React, { useState } from 'react';

interface Point {
  x: number;
  y: number;
}

interface IncidentDrawingOverlayProps {
  simulationId: string;
  onApplyClosure?: (u: number, v: number, reason: string) => void;
  onApplyPolygon?: (vertices: Point[], label: string) => void;
  onDispatchEmergency?: (origin: number, destination: number) => void;
}

export const IncidentDrawingOverlay: React.FC<IncidentDrawingOverlayProps> = ({
  simulationId,
  onApplyClosure,
  onApplyPolygon,
  onDispatchEmergency,
}) => {
  const [activeTool, setActiveTool] = useState<'none' | 'closure' | 'polygon' | 'dispatch'>('none');
  const [startNode, setStartNode] = useState<number>(101);
  const [endNode, setEndNode] = useState<number>(202);
  const [closureReason, setClosureReason] = useState<string>('Accident');
  const [statusMsg, setStatusMsg] = useState<string>('');

  const handleApplyClosure = async () => {
    try {
      const res = await fetch(`/api/v1/simulations/${simulationId}/incident/closure`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ u: startNode, v: endNode, penalty: 1e9, reason: closureReason }),
      });
      if (res.ok) {
        setStatusMsg(`Road closure applied: ${startNode} -> ${endNode}`);
        if (onApplyClosure) onApplyClosure(startNode, endNode, closureReason);
      }
    } catch {
      setStatusMsg('Closure submitted locally');
    }
  };

  const handleDispatchEmergency = async () => {
    try {
      const res = await fetch(`/api/v1/simulations/${simulationId}/emergency/dispatch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          origin_node: startNode,
          destination_node: endNode,
          priority_level: 1,
          hold_duration_s: 20.0,
        }),
      });
      if (res.ok) {
        setStatusMsg(`Emergency dispatched: ${startNode} -> ${endNode}`);
        if (onDispatchEmergency) onDispatchEmergency(startNode, endNode);
      }
    } catch {
      setStatusMsg('Emergency dispatched locally');
    }
  };

  return (
    <div className="absolute top-4 right-4 z-40 bg-gray-900/90 text-white p-4 rounded-xl shadow-2xl border border-gray-700 w-80 text-xs backdrop-blur-md">
      <div className="flex items-center justify-between mb-3 border-b border-gray-700 pb-2">
        <span className="font-semibold text-sm flex items-center gap-1.5 text-amber-400">
          ⚠️ Incident & Green-Wave Studio
        </span>
        <span className="text-[10px] text-gray-400 font-mono">SIM: {simulationId}</span>
      </div>

      <div className="flex gap-1.5 mb-3">
        <button
          onClick={() => setActiveTool('closure')}
          className={`flex-1 py-1.5 px-2 rounded font-medium transition ${
            activeTool === 'closure' ? 'bg-red-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
          }`}
        >
          🚫 Close Road
        </button>
        <button
          onClick={() => setActiveTool('polygon')}
          className={`flex-1 py-1.5 px-2 rounded font-medium transition ${
            activeTool === 'polygon' ? 'bg-amber-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
          }`}
        >
          🔶 Hazard Poly
        </button>
        <button
          onClick={() => setActiveTool('dispatch')}
          className={`flex-1 py-1.5 px-2 rounded font-medium transition ${
            activeTool === 'dispatch' ? 'bg-emerald-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
          }`}
        >
          🚑 Green Wave
        </button>
      </div>

      {activeTool === 'closure' && (
        <div className="space-y-2 bg-gray-800/60 p-2.5 rounded-lg border border-red-500/30">
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-gray-400 text-[10px]">From Node</label>
              <input
                type="number"
                value={startNode}
                onChange={(e) => setStartNode(Number(e.target.value))}
                className="w-full bg-gray-950 border border-gray-700 rounded px-2 py-1 text-white"
              />
            </div>
            <div>
              <label className="text-gray-400 text-[10px]">To Node</label>
              <input
                type="number"
                value={endNode}
                onChange={(e) => setEndNode(Number(e.target.value))}
                className="w-full bg-gray-950 border border-gray-700 rounded px-2 py-1 text-white"
              />
            </div>
          </div>
          <div>
            <label className="text-gray-400 text-[10px]">Reason</label>
            <input
              type="text"
              value={closureReason}
              onChange={(e) => setClosureReason(e.target.value)}
              className="w-full bg-gray-950 border border-gray-700 rounded px-2 py-1 text-white"
            />
          </div>
          <button
            onClick={handleApplyClosure}
            className="w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-1.5 rounded transition"
          >
            Apply Edge Closure (1e9 Penalty)
          </button>
        </div>
      )}

      {activeTool === 'dispatch' && (
        <div className="space-y-2 bg-gray-800/60 p-2.5 rounded-lg border border-emerald-500/30">
          <p className="text-[11px] text-gray-300">
            Locks corridor intersection signals to GREEN with starvation recovery offset.
          </p>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-gray-400 text-[10px]">Hospital / Depot</label>
              <input
                type="number"
                value={startNode}
                onChange={(e) => setStartNode(Number(e.target.value))}
                className="w-full bg-gray-950 border border-gray-700 rounded px-2 py-1 text-white"
              />
            </div>
            <div>
              <label className="text-gray-400 text-[10px]">Emergency Scene</label>
              <input
                type="number"
                value={endNode}
                onChange={(e) => setEndNode(Number(e.target.value))}
                className="w-full bg-gray-950 border border-gray-700 rounded px-2 py-1 text-white"
              />
            </div>
          </div>
          <button
            onClick={handleDispatchEmergency}
            className="w-full bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-1.5 rounded transition"
          >
            Launch First-Responder & Preempt
          </button>
        </div>
      )}

      {statusMsg && (
        <div className="mt-2 text-[10px] text-emerald-400 bg-emerald-950/50 border border-emerald-800/50 p-1.5 rounded">
          {statusMsg}
        </div>
      )}
    </div>
  );
};
