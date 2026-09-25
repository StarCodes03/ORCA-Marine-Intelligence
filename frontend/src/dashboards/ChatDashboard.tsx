import React from 'react';
import { ChatPanel } from '../components/ChatPanel';
import type { ChatResponse, NearestPFZ } from '../services/api';
import type { RoleConfig } from '../config/roles';

interface Message {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  responsePayload?: ChatResponse;
  timestamp: string;
}

interface ChatDashboardProps {
  messages: Message[];
  onSendMessage: (msg: string, vesselType?: string, languageMode?: string) => void;
  isLoading: boolean;
  onSelectPfz?: (pfz: NearestPFZ) => void;
  latestResponse?: ChatResponse | null;
  hasQueried?: boolean;
  selectedVessel?: string;
  onVesselChange?: (vessel: string) => void;
  selectedLanguage?: string;
  onLanguageChange?: (lang: string) => void;
  onNavigateToMarine?: () => void;
  onNavigateToRoute?: () => void;
  activeRole?: RoleConfig;
  onSwitchRole?: () => void;
}

export const ChatDashboard: React.FC<ChatDashboardProps> = ({
  messages,
  onSendMessage,
  isLoading,
  onSelectPfz,
  latestResponse,
  hasQueried,
  selectedVessel,
  onVesselChange,
  selectedLanguage,
  onLanguageChange,
  onNavigateToMarine,
  onNavigateToRoute,
  activeRole,
  onSwitchRole,
}) => {
  const handleSelectPfz = (pfz: NearestPFZ) => {
    if (onSelectPfz) onSelectPfz(pfz);
    if (onNavigateToMarine) onNavigateToMarine();
  };

  return (
    <div className="workspace-pane chat-workspace-pane">
      <div className="chat-dashboard-container">
        <ChatPanel
          messages={messages}
          onSendMessage={onSendMessage}
          isLoading={isLoading}
          onSelectPfz={handleSelectPfz}
          latestResponse={latestResponse}
          hasQueried={hasQueried}
          selectedVessel={selectedVessel}
          onVesselChange={onVesselChange}
          selectedLanguage={selectedLanguage}
          onLanguageChange={onLanguageChange}
          onNavigateToMarine={onNavigateToMarine}
          onNavigateToRoute={onNavigateToRoute}
          activeRole={activeRole}
          onSwitchRole={onSwitchRole}
        />
      </div>
    </div>
  );
};
