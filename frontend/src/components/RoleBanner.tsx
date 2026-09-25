import React, { useState } from 'react';
import { Sparkles, HelpCircle, ChevronDown, ChevronUp, Users, Info } from 'lucide-react';
import type { RoleConfig } from '../config/roles';

interface RoleBannerProps {
  activeRole: RoleConfig;
  onSwitchRole: () => void;
  onSelectPrompt?: (prompt: string) => void;
  compact?: boolean;
}

export const RoleBanner: React.FC<RoleBannerProps> = ({
  activeRole,
  onSwitchRole,
  onSelectPrompt,
  compact = false,
}) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(!compact);

  return (
    <div className={`role-banner-container ${compact ? 'compact' : ''}`}>
      <div className="role-banner-main-row">
        <div className="role-banner-identity">
          <span className="role-banner-icon">{activeRole.icon}</span>
          <div className="role-banner-text">
            <div className="role-banner-title-line">
              <span className="role-banner-name">{activeRole.displayName}</span>
              <span className="role-banner-badge">ROLE ACTIVE</span>
            </div>
            <div className="role-banner-tagline">{activeRole.tagline}</div>
          </div>
        </div>

        <div className="role-banner-actions">
          <button
            type="button"
            className="role-switch-btn"
            onClick={onSwitchRole}
            title="Change active marine role persona"
          >
            <Users size={13} />
            <span>Switch Role</span>
          </button>

          <button
            type="button"
            className="role-banner-toggle-btn"
            onClick={() => setIsExpanded(!isExpanded)}
            title={isExpanded ? 'Hide priorities' : 'Show priorities'}
            aria-expanded={isExpanded}
          >
            {isExpanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      </div>

      {isExpanded && (
        <div className="role-banner-expanded-content">
          {/* Priorities Strip */}
          <div className="role-banner-priorities-section">
            <div className="role-banner-section-label">
              <Sparkles size={12} color="#06b6d4" />
              <span>ROLE PRIORITIES:</span>
            </div>
            <div className="role-banner-pills-wrap">
              {activeRole.priorities.map((pri, idx) => (
                <span key={idx} className="role-banner-pill">
                  {pri}
                </span>
              ))}
            </div>
          </div>

          {/* Suggested Quick Questions */}
          {onSelectPrompt && activeRole.suggestedQuestions.length > 0 && (
            <div className="role-banner-questions-section">
              <div className="role-banner-section-label">
                <HelpCircle size={12} color="#38bdf8" />
                <span>SUGGESTED QUESTIONS:</span>
              </div>
              <div className="role-banner-prompts-wrap">
                {activeRole.suggestedQuestions.map((q, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="role-prompt-chip-btn"
                    onClick={() => onSelectPrompt(q)}
                  >
                    <span>👉 {q}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Role-Specific Operational Notice */}
          {activeRole.terminology.roleDisclaimer && (
            <div className="role-banner-disclaimer-box">
              <Info size={12} color="#94a3b8" />
              <span>{activeRole.terminology.roleDisclaimer}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
