import React, { useState } from 'react';
import { MetricsPanel } from './MetricsPanel';
import { CongestionCVOverlay } from './CongestionCVOverlay';
import { VirtualCameraPanel } from './VirtualCameraPanel';
import { ChatPanel } from './ChatPanel';
import { IncidentReportPanel } from './IncidentReportPanel';
import { AlgoExplorerPanel } from './AlgoExplorer/AlgoExplorerPanel';
import { EmissionsPanel } from './EmissionsPanel';
import { XaiInspectionDrawer } from './XaiInspectionDrawer';
import type { IntersectionSignalState, SignalMode } from '../hooks/useWebSocket';

interface ZoneMetric {
  zone_id: number;
  wait_time: number;
}

interface RightDockProps {
  metrics: {
    avg_speed?: number;
    active_agents?: number;
    completed_agents?: number;
    avg_wait_time?: number;
    gini_coefficient?: number;
  } | null;
  zoneMetrics?: ZoneMetric[];
  signalMode?: SignalMode;
  connected?: boolean;
  simActive?: boolean;
  onSwitch?: (policy: 'webster' | 'rl' | 'fuzzy' | 'type2_fuzzy') => void;
  signals?: IntersectionSignalState[];
  onSwitchPolicy?: (policy: 'webster' | 'rl' | 'fuzzy' | 'type2_fuzzy', intersectionId?: number | null) => void;
  simTick?: number | null;
  city: string | null;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

type TabType = 'metrics' | 'xai' | 'vision' | 'chat' | 'algos' | 'emissions' | 'all';

const TABS: { id: TabType; label: string; icon: string }[] = [
  { id: 'metrics', label: 'Metrics', icon: '📊' },
  { id: 'xai', label: 'XAI', icon: '🧠' },
  { id: 'vision', label: 'Vision', icon: '👁️' },
  { id: 'chat', label: 'Chat', icon: '💬' },
  { id: 'algos', label: 'Algos', icon: '🧪' },
  { id: 'emissions', label: 'Carbon', icon: '🌱' },
  { id: 'all', label: 'All', icon: '📑' },
];

export const RightDock: React.FC<RightDockProps> = ({
  metrics,
  zoneMetrics,
  signalMode,
  connected = false,
  simActive = false,
  onSwitch,
  signals = [],
  onSwitchPolicy,
  simTick = null,
  city,
  collapsed,
  onToggleCollapse,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('metrics');
  const [selectedIntersectionId, setSelectedIntersectionId] = useState<number | null>(null);

  if (!metrics && !simActive) {
    return null;
  }

  if (collapsed) {
    return (
      <button
        onClick={onToggleCollapse}
        aria-label="Expand Analytics Dock"
        style={{
          position: 'absolute',
          top: '20px',
          right: '20px',
          zIndex: 1000,
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '8px 14px',
          border: '1px solid #374151',
          borderRadius: '8px',
          cursor: 'pointer',
          backgroundColor: 'rgba(17, 24, 39, 0.95)',
          color: '#e5e7eb',
          fontFamily: 'system-ui, sans-serif',
          fontSize: '12px',
          fontWeight: 600,
          boxShadow: '0 10px 15px -3px rgba(0, 0, 0, 0.3)',
        }}
      >
        <span>📊</span>
        <span>Analytics Dock</span>
      </button>
    );
  }

  return (
    <div
      style={{
        position: 'absolute',
        top: '20px',
        right: '20px',
        bottom: '20px',
        width: '380px',
        zIndex: 1000,
        display: 'flex',
        flexDirection: 'column',
        backgroundColor: 'rgba(17, 24, 39, 0.95)',
        backdropFilter: 'blur(8px)',
        border: '1px solid #374151',
        borderRadius: '12px',
        overflow: 'hidden',
        boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.4)',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      {/* Top Bar: Tabs & Collapse Button */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: '1px solid rgba(55, 65, 81, 0.8)',
          backgroundColor: 'rgba(15, 23, 42, 0.6)',
          padding: '0 4px',
        }}
      >
        <div style={{ display: 'flex', gap: '2px', overflowX: 'auto', padding: '4px 0' }}>
          {TABS.map((tab) => {
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '4px',
                  padding: '6px 8px',
                  border: 'none',
                  borderBottom: isActive ? '2px solid #3b82f6' : '2px solid transparent',
                  borderRadius: '4px 4px 0 0',
                  cursor: 'pointer',
                  fontSize: '11px',
                  fontWeight: 600,
                  backgroundColor: isActive ? 'rgba(59, 130, 246, 0.15)' : 'transparent',
                  color: isActive ? '#60a5fa' : '#9ca3af',
                  transition: 'all 0.15s',
                  whiteSpace: 'nowrap',
                }}
              >
                <span>{tab.icon}</span>
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        <button
          onClick={onToggleCollapse}
          aria-label="Collapse Dock"
          title="Collapse Analytics Dock"
          style={{
            background: 'transparent',
            border: 'none',
            color: '#9ca3af',
            fontSize: '14px',
            cursor: 'pointer',
            padding: '4px 8px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          —
        </button>
      </div>

      {/* Scrollable Content Body */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: '14px',
          display: 'flex',
          flexDirection: 'column',
          gap: '12px',
        }}
      >
        {activeTab === 'metrics' && (
          <MetricsPanel
            metrics={metrics}
            zoneMetrics={zoneMetrics}
            signalMode={signalMode}
            connected={connected}
            simActive={simActive}
            onSwitch={onSwitch}
            signals={signals}
            onSwitchPolicy={onSwitchPolicy}
            embedded={true}
          />
        )}

        {activeTab === 'xai' && (
          <div>
            {signals.length > 1 && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <span style={{ fontSize: '11px', color: '#9ca3af' }}>Select Junction:</span>
                <select
                  value={selectedIntersectionId ?? (signals[0]?.id ?? 0)}
                  onChange={(e) => setSelectedIntersectionId(Number(e.target.value))}
                  style={{
                    backgroundColor: '#1f2937',
                    border: '1px solid #374151',
                    borderRadius: '6px',
                    color: '#e5e7eb',
                    fontSize: '11px',
                    padding: '3px 6px',
                  }}
                >
                  {signals.map((s) => (
                    <option key={s.id} value={s.id}>
                      Intersection #{s.id}
                    </option>
                  ))}
                </select>
                {simTick !== null && (
                  <span style={{ fontSize: '10px', color: '#6b7280', marginLeft: 'auto' }}>
                    Tick {simTick.toLocaleString()}
                  </span>
                )}
              </div>
            )}
            <XaiInspectionDrawer
              isOpen={true}
              onClose={() => setActiveTab('metrics')}
              selectedIntersectionId={selectedIntersectionId ?? (signals.length > 0 ? signals[0].id : null)}
              signals={signals}
              currentMode={signalMode}
              onSwitchPolicy={onSwitchPolicy}
            />
          </div>
        )}

        {activeTab === 'vision' && (
          <>
            <CongestionCVOverlay city={city || 'chicago'} visible={true} />
            <VirtualCameraPanel visible={true} />
          </>
        )}

        {activeTab === 'chat' && (
          <>
            <ChatPanel city={city || 'chicago'} visible={true} />
            <IncidentReportPanel city={city || 'chicago'} visible={true} />
          </>
        )}

        {activeTab === 'algos' && <AlgoExplorerPanel />}

        {activeTab === 'emissions' && <EmissionsPanel />}

        {activeTab === 'all' && (
          <>
            <MetricsPanel
              metrics={metrics}
              zoneMetrics={zoneMetrics}
              signalMode={signalMode}
              connected={connected}
              simActive={simActive}
              onSwitch={onSwitch}
              signals={signals}
              onSwitchPolicy={onSwitchPolicy}
              embedded={true}
            />
            <div style={{ height: '1px', backgroundColor: 'rgba(55, 65, 81, 0.6)', margin: '4px 0' }} />
            <CongestionCVOverlay city={city || 'chicago'} visible={true} />
            <VirtualCameraPanel visible={true} />
            <div style={{ height: '1px', backgroundColor: 'rgba(55, 65, 81, 0.6)', margin: '4px 0' }} />
            <ChatPanel city={city || 'chicago'} visible={true} />
            <IncidentReportPanel city={city || 'chicago'} visible={true} />
            <div style={{ height: '1px', backgroundColor: 'rgba(55, 65, 81, 0.6)', margin: '4px 0' }} />
            <AlgoExplorerPanel />
            <div style={{ height: '1px', backgroundColor: 'rgba(55, 65, 81, 0.6)', margin: '4px 0' }} />
            <EmissionsPanel />
          </>
        )}
      </div>
    </div>
  );
};

export default RightDock;
