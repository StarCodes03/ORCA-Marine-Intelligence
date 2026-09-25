import React from 'react';
import { X, Check, Compass, Shield, ArrowRight } from 'lucide-react';
import { getAllRoles, type RoleConfig } from '../config/roles';

interface RoleSelectionModalProps {
  isOpen: boolean;
  activeRole?: RoleConfig;
  currentRole?: RoleConfig;
  onSelectRole: (role: RoleConfig) => void;
  onClose: () => void;
  canClose?: boolean;
}

export const RoleSelectionModal: React.FC<RoleSelectionModalProps> = ({
  isOpen,
  activeRole,
  currentRole,
  onSelectRole,
  onClose,
  canClose = true,
}) => {
  if (!isOpen) return null;

  const allRoles = getAllRoles();
  const effectiveRole = activeRole || currentRole;

  return (
    <div className="role-modal-overlay" role="dialog" aria-modal="true" aria-labelledby="role-modal-title">
      <div className="role-modal-backdrop" onClick={canClose ? onClose : undefined} />
      
      <div className="role-modal-container">
        {/* Modal Header */}
        <div className="role-modal-header">
          <div className="role-modal-brand-strip">
            <div className="role-modal-brand-badge">
              <Compass size={18} color="#06b6d4" />
              <span>ORCA MARINE INTELLIGENCE</span>
            </div>
            {canClose && (
              <button
                type="button"
                className="role-modal-close-btn"
                onClick={onClose}
                aria-label="Close role selection"
              >
                <X size={18} />
              </button>
            )}
          </div>

          <h2 id="role-modal-title" className="role-modal-title">
            Welcome to ORCA 🌊
          </h2>
          <p className="role-modal-subtitle">
            Choose how you use marine intelligence. ORCA tailors your priorities, suggested queries, and map focus while running on the same verified live data and reasoning core.
          </p>
        </div>

        {/* 9 Role Cards Grid */}
        <div className="role-cards-grid">
          {allRoles.map((role) => {
            const isSelected = effectiveRole?.id === role.id;
            return (
              <div
                key={role.id}
                className={`role-card ${isSelected ? 'selected' : ''}`}
                onClick={() => onSelectRole(role)}
                tabIndex={0}
                role="button"
                aria-pressed={isSelected}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onSelectRole(role);
                  }
                }}
              >
                <div className="role-card-top">
                  <div className="role-card-icon-box">
                    <span className="role-card-emoji">{role.icon}</span>
                  </div>
                  {isSelected && (
                    <div className="role-card-selected-badge" title="Active Role">
                      <Check size={12} strokeWidth={3} />
                      <span>Active</span>
                    </div>
                  )}
                </div>

                <div className="role-card-content">
                  <h3 className="role-card-name">{role.displayName}</h3>
                  <p className="role-card-tagline">{role.tagline}</p>
                </div>

                {/* Priority Badges Strip */}
                <div className="role-card-priorities">
                  {role.priorities.slice(0, 3).map((pri, idx) => (
                    <span key={idx} className="role-priority-pill">
                      {pri}
                    </span>
                  ))}
                  {role.priorities.length > 3 && (
                    <span className="role-priority-more">
                      +{role.priorities.length - 3} more
                    </span>
                  )}
                </div>

                <div className="role-card-footer">
                  <span className="role-card-action-text">
                    {isSelected ? 'Currently Selected' : 'Select Role'}
                  </span>
                  <ArrowRight size={13} className="role-card-arrow" />
                </div>
              </div>
            );
          })}
        </div>

        {/* Modal Footer */}
        <div className="role-modal-footer">
          <div className="role-modal-footer-disclaimer">
            <Shield size={13} color="#38bdf8" />
            <span>
              One Shared Platform • One Deterministic Collective • No Separate Silos or Fabricated Data • Switch Anytime
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};
