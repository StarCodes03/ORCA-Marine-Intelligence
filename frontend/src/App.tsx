import React, { useState, useEffect } from 'react';
import { Header } from './components/Header';
import { Sidebar, type DashboardRoute } from './components/Sidebar';
import { ChatDashboard } from './dashboards/ChatDashboard';
import { MarineIntelligenceDashboard } from './dashboards/MarineIntelligenceDashboard';
import { RouteSafetyDashboard } from './dashboards/RouteSafetyDashboard';
import { DataEvidenceDashboard } from './dashboards/DataEvidenceDashboard';
import { checkHealth, getSpatialLayers, sendChatMessage } from './services/api';
import type {
  ChatResponse,
  LocationCoords,
  NearestPFZ,
  WeatherData,
  OceanData,
  GeospatialData
} from './services/api';

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
  const [latestWeather, setLatestWeather] = useState<WeatherData | null>(null);
  const [latestOcean, setLatestOcean] = useState<OceanData | null>(null);
  const [latestGeospatial, setLatestGeospatial] = useState<GeospatialData | null>(null);
  const [hasQueried, setHasQueried] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [selectedVessel, setSelectedVessel] = useState<string>('motorized_frp_obm');
  const [selectedLanguage, setSelectedLanguage] = useState<string>('english');

  // Lightweight routing initialized from browser pathname (defaults to /chat)
  const getInitialRoute = (): DashboardRoute => {
    const path = window.location.pathname;
    if (path === '/marine' || path === '/route' || path === '/evidence') {
      return path;
    }
    return '/chat';
  };

  const [activeRoute, setActiveRoute] = useState<DashboardRoute>(getInitialRoute);

  const navigateTo = (route: DashboardRoute) => {
    setActiveRoute(route);
    if (window.location.pathname !== route) {
      window.history.pushState(null, '', route);
    }
  };

  // Synchronize with browser back/forward buttons
  useEffect(() => {
    const handlePopState = () => {
      const path = window.location.pathname;
      if (path === '/marine' || path === '/route' || path === '/evidence' || path === '/chat') {
        setActiveRoute(path as DashboardRoute);
      } else {
        setActiveRoute('/chat');
      }
    };

    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Initial conversational greeting message
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'init-1',
      sender: 'assistant',
      text: "Welcome to ORCA — your conversational marine intelligence assistant for Kochi and the Arabian Sea coastal sector.\n\nAsk me about fishing safety, weather and sea conditions, or safe passage corridors to Potential Fishing Zones.",
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    },
  ]);

  // Load backend health and spatial layers on mount
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
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
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
      setHasQueried(true);

      if (response.weather) setLatestWeather(response.weather);
      if (response.ocean) setLatestOcean(response.ocean);
      if (response.geospatial) setLatestGeospatial(response.geospatial);

      // If response has spatial features or geospatial data, identify target PFZ
      const targetPfz = response.spatial_features?.nearest_pfz || response.geospatial?.nearest_pfz || null;
      if (targetPfz) {
        setNearestPfz(targetPfz);
      }

      const assistantMsg: Message = {
        id: 'asst-' + Date.now(),
        sender: 'assistant',
        text: response.answer,
        responsePayload: response,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (error: any) {
      console.error('Error querying ORCA agent collective:', error);
      const errorMsg: Message = {
        id: 'err-' + Date.now(),
        sender: 'assistant',
        text: `⚠️ Agent Communication Error: ${error.message || 'Failed to reach backend API. Ensure FastAPI is running.'}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  const effectiveLatestResponse: ChatResponse | null = latestResponse ? {
    ...latestResponse,
    weather: latestResponse.weather || latestWeather,
    ocean: latestResponse.ocean || latestOcean,
    geospatial: latestResponse.geospatial || latestGeospatial,
  } : null;

  return (
    <div className="app-container">
      {/* Top Application Header */}
      <Header
        systemHealthy={systemHealthy}
        sectorName="Kochi Coastal Sector, Kerala"
        latestResponse={effectiveLatestResponse}
        hasQueried={hasQueried}
      />

      {/* Persistent Shell Layout: Sidebar + Active Workspace */}
      <div className="app-shell">
        <Sidebar
          activeRoute={activeRoute}
          onNavigate={navigateTo}
          systemHealthy={systemHealthy}
        />

        {/* Dynamic Workspace Container */}
        <main className="main-workspace-container" role="main">
          {activeRoute === '/chat' && (
            <ChatDashboard
              messages={messages}
              onSendMessage={handleSendMessage}
              isLoading={isLoading}
              onSelectPfz={(pfz) => setNearestPfz(pfz)}
              latestResponse={effectiveLatestResponse}
              hasQueried={hasQueried}
              selectedVessel={selectedVessel}
              onVesselChange={setSelectedVessel}
              selectedLanguage={selectedLanguage}
              onLanguageChange={setSelectedLanguage}
              onNavigateToMarine={() => navigateTo('/marine')}
              onNavigateToRoute={() => navigateTo('/route')}
            />
          )}

          {activeRoute === '/marine' && (
            <MarineIntelligenceDashboard
              vesselLocation={vesselLocation}
              nearestPfz={nearestPfz}
              spatialLayers={spatialLayers}
              transitRoute={effectiveLatestResponse?.transit_route}
              onSelectPfz={(pfz) => setNearestPfz(pfz)}
              onNavigateToRoute={() => navigateTo('/route')}
            />
          )}

          {activeRoute === '/route' && (
            <RouteSafetyDashboard
              vesselLocation={vesselLocation}
              nearestPfz={nearestPfz}
              spatialLayers={spatialLayers}
              latestResponse={effectiveLatestResponse}
              selectedVessel={selectedVessel}
              onVesselChange={setSelectedVessel}
              onNavigateToChat={() => navigateTo('/chat')}
              onSelectPfz={(pfz) => setNearestPfz(pfz)}
            />
          )}

          {activeRoute === '/evidence' && (
            <DataEvidenceDashboard
              latestResponse={effectiveLatestResponse}
              hasQueried={hasQueried}
            />
          )}
        </main>
      </div>
    </div>
  );
};

export default App;
