import React from 'react';
import { ChatPanel } from '../components/ChatPanel';
import type { ChatResponse, NearestPFZ } from '../services/api';

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
  selectedVessel?: string;
  onVesselChange?: (vessel: string) => void;
  selectedLanguage?: string;
  onLanguageChange?: (lang: string) => void;
  onNavigateToMarine?: () => void;
}

export const ChatDashboard: React.FC<ChatDashboardProps> = ({
  messages,
  onSendMessage,
  isLoading,
  onSelectPfz,
  latestResponse,
  selectedVessel,
  onVesselChange,
  selectedLanguage,
  onLanguageChange,
  onNavigateToMarine,
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
          selectedVessel={selectedVessel}
          onVesselChange={onVesselChange}
          selectedLanguage={selectedLanguage}
          onLanguageChange={onLanguageChange}
        />
      </div>
    </div>
  );
};
