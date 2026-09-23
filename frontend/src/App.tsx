import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { MarineMap } from './map/MarineMap';
import { ChatPanel } from './components/ChatPanel';
import { AgentTraceDrawer } from './components/AgentTraceDrawer';
import { checkHealth, getSpatialLayers, sendChatMessage } from './services/api';
import type { ChatResponse, LocationCoords, NearestPFZ } from './services/api';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  responsePayload?: ChatResponse;
  timestamp: string;
}

export const App: React.FC = () => {
  const [systemHealthy, setSystemHealthy] = useState<boolean>(false);
  const [spatialLayers, setSpatialLayers] = useState<any>(null);
  const [vesselLocation] = useState<LocationCoords>({
    name: 'Demo Vessel (Kochi Sector)',
    latitude: 9.9450,
    longitude: 76.2150
  });
  const [nearestPfz, setNearestPfz] = useState<NearestPFZ | null>(null);
  const [latestResponse, setLatestResponse] = useState<ChatResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [selectedVessel, setSelectedVessel] = useState<string>('motorized_frp_obm');
  const [selectedLanguage, setSelectedLanguage] = useState<string>('bilingual');

  // Initial greeting message
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'init-1',
      sender: 'assistant',
      text: "Welcome to ORCA (Marine Ecosystem Reasoning with Collaborative Agents).\n\nI am your agentic marine intelligence advisor for Kochi and the Arabian Sea coastal sector. You can test safety for fishing expeditions, locate nearest Potential Fishing Zones (PFZs), or inspect marine meteorology.",
      timestamp: new Date().toLocaleTimeString(),
    },
  ]);

  // Load health and spatial layers on mount
  useEffect(() => {
    async function initSystem() {
      try {
        const health = await checkHealth();
        setSystemHealthy(health.status === 'healthy');
      } catch (err) {
        console.warn('Backend not yet reachable on mount:', err);
        setSystemHealthy(false);
      }

      try {
        const layers = await getSpatialLayers();
        setSpatialLayers(layers);
      } catch (err) {
        console.warn('Could not load spatial layers:', err);
      }
    }

    initSystem();
    const interval = setInterval(initSystem, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleSendMessage = async (userPrompt: string, vesselTypeOverride?: string, languageModeOverride?: string) => {
    const vesselToUse = vesselTypeOverride || selectedVessel;
    const langToUse = languageModeOverride || selectedLanguage;

    const userMsg: Message = {
      id: 'user-' + Date.now(),
      sender: 'user',
      text: userPrompt,
      timestamp: new Date().toLocaleTimeString(),
    };

    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response = await sendChatMessage(
        userPrompt,
        'demo-conv-001',
        vesselLocation.latitude,
        vesselLocation.longitude,
        vesselToUse,
        langToUse
      );

      setLatestResponse(response);

      // If response has spatial features or geospatial data, identify nearest PFZ
      const targetPfz = response.spatial_features?.nearest_pfz || response.geospatial?.nearest_pfz || null;
      if (targetPfz) {
        setNearestPfz(targetPfz);
      }

      const assistantMsg: Message = {
        id: 'asst-' + Date.now(),
        sender: 'assistant',
        text: response.answer,
        responsePayload: response,
        timestamp: new Date().toLocaleTimeString(),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (error: any) {
      console.error('Error querying ORCA agent collective:', error);
      const errorMsg: Message = {
        id: 'err-' + Date.now(),
        sender: 'assistant',
        text: `⚠️ Agent Communication Error: ${error.message || 'Failed to reach backend API. Ensure FastAPI is running.'}`,
        timestamp: new Date().toLocaleTimeString(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Top Application Header */}
      <Header
        systemHealthy={systemHealthy}
        sectorName="Kochi & Arabian Sea Sector, Kerala"
        latestResponse={latestResponse}
      />

      {/* Main Workspace Split View */}
      <div className="main-workspace">
        {/* Left: Interactive Marine Map */}
        <MarineMap
          vesselLocation={vesselLocation}
          nearestPfz={nearestPfz}
          spatialLayers={spatialLayers}
          highlightRoute={Boolean(nearestPfz || latestResponse?.transit_route)}
          transitRoute={latestResponse?.transit_route}
        />

        {/* Right: Conversational Intelligence Panel */}
        <ChatPanel
          messages={messages}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          onSelectPfz={(pfz) => setNearestPfz(pfz)}
          latestResponse={latestResponse}
          selectedVessel={selectedVessel}
          onVesselChange={setSelectedVessel}
          selectedLanguage={selectedLanguage}
          onLanguageChange={setSelectedLanguage}
        />

        {/* Collapsible Bottom: Developer Agent Trace & Audit Log */}
        <AgentTraceDrawer latestResponse={latestResponse} />
      </div>
    </div>
  );
};

export default App;
