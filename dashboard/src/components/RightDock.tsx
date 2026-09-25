import React, { useState } from 'react';
import { MetricsPanel } from './MetricsPanel';
import { CongestionCVOverlay } from './CongestionCVOverlay';
import { VirtualCameraPanel } from './VirtualCameraPanel';
import { ChatPanel } from './ChatPanel';
import { IncidentReportPanel } from './IncidentReportPanel';
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
  onSwitch?: (policy: 'webster' | 'rl') => void;
  signals?: IntersectionSignalState[];
  onSwitchPolicy?: (policy: 'webster' | 'rl' | 'fuzzy', intersectionId?: number | null) => void;
  city: string | null;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

type TabType = 'metrics' | 'vision' | 'chat' | 'all';

const TABS: { id: TabType; label: string; icon: string }[] = [
  { id: 'metrics', label: 'Metrics', icon: '📊' },
  { id: 'vision', label: 'Vision', icon: '👁️' },
  { id: 'chat', label: 'Chat', icon: '💬' },
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
  city,
  collapsed,
  onToggleCollapse,
}) => {
  const [activeTab, setActiveTab] = useState<TabType>('metrics');

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
          backgroundColor: 'rgba(17, 24, 39, 0.95)',
          backdropFilter: 'blur(8px)',
          border: '1px solid #374151',
          borderRadius: '8px',
          color: '#e5e7eb',
          cursor: 'pointer',
          fontSize: '13px',
          fontWeight: 600,
          boxShadow: '0 10px 25px rgba(0, 0, 0, 0.4)',
          transition: 'all 0.2s',
          whiteSpace: 'nowrap',
        }}
      >
        <span>📊</span>
        <span>Analytics Dock</span>
        <span style={{ fontSize: '12px', color: '#60a5fa', fontWeight: 'bold' }}>+</span>
      </button>
    );
  }

  return (
    <div
      style={{
        position: 'absolute',
        top: '20px',
        right: '20px',
        bottom: '80px',
        width: '340px',
        maxHeight: 'calc(100vh - 100px)',
        zIndex: 1000,
        backgroundColor: 'rgba(17, 24, 39, 0.95)',
        backdropFilter: 'blur(12px)',
        color: '#ffffff',
        borderRadius: '12px',
        boxShadow: '0 20px 40px -10px rgba(0, 0, 0, 0.5)',
        border: '1px solid #374151',
        display: 'flex',
        flexDirection: 'column',
        overflow: 'hidden',
        fontFamily: 'system-ui, sans-serif',
      }}
    >
      {/* Header with Navigation Tabs and Minimize Button */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '8px 10px',
          borderBottom: '1px solid rgba(55, 65, 81, 0.7)',
          backgroundColor: 'rgba(15, 23, 42, 0.6)',
        }}
      >
        <div style={{ display: 'flex', gap: '4px', flex: 1, overflowX: 'auto' }}>
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
                  padding: '5px 8px',
                  borderRadius: '6px',
                  border: isActive ? '1px solid #3b82f6' : '1px solid transparent',
                  backgroundColor: isActive ? 'rgba(59, 130, 246, 0.25)' : 'transparent',
                  color: isActive ? '#ffffff' : '#9ca3af',
                  fontSize: '11px',
                  fontWeight: 600,
                  cursor: 'pointer',
                  transition: 'all 0.15s ease-in-out',
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
          title="Minimize Dock"
          aria-label="Minimize Dock"
          style={{
            marginLeft: '4px',
            backgroundColor: 'transparent',
            border: 'none',
            color: '#9ca3af',
            cursor: 'pointer',
            padding: '4px 6px',
            borderRadius: '4px',
            fontSize: '14px',
            fontWeight: 'bold',
            lineHeight: 1,
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
          </>
        )}
      </div>
    </div>
  );
};

export default RightDock;
