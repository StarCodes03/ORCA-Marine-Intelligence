import React from 'react';
import { MessageSquare, Map, Navigation, Database, Compass, ShieldCheck } from 'lucide-react';

export type DashboardRoute = '/chat' | '/marine' | '/route' | '/evidence';

interface SidebarProps {
  activeRoute: DashboardRoute;
  onNavigate: (route: DashboardRoute) => void;
  systemHealthy: boolean;
}

interface NavItem {
  id: DashboardRoute;
  label: string;
  shortLabel: string;
  icon: React.ReactNode;
  badge?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({
  activeRoute,
  onNavigate,
  systemHealthy,
}) => {
  const navItems: NavItem[] = [
    {
      id: '/chat',
      label: 'ORCA Chat',
      shortLabel: 'Chat',
      icon: <MessageSquare size={17} />,
    },
    {
      id: '/marine',
      label: 'Marine Intelligence',
      shortLabel: 'Marine',
      icon: <Map size={17} />,
    },
    {
      id: '/route',
      label: 'Route & Safety',
      shortLabel: 'Route',
      icon: <Navigation size={17} />,
    },
    {
      id: '/evidence',
      label: 'Data & Evidence',
      shortLabel: 'Evidence',
      icon: <Database size={17} />,
    },
  ];

  return (
    <aside className="orca-sidebar" aria-label="Main Navigation">
      {/* Brand Header */}
      <div className="sidebar-brand">
        <div className="sidebar-brand-icon">
          <Compass size={20} />
        </div>
        <div className="sidebar-brand-text">
          <div className="sidebar-brand-title">ORCA</div>
          <div className="sidebar-brand-subtitle">Marine Ecosystem Intelligence</div>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="sidebar-nav">
        <div className="sidebar-nav-section-title">WORKSPACES</div>
        {navItems.map((item) => {
          const isActive = activeRoute === item.id;
          return (
            <button
              key={item.id}
              type="button"
              className={`sidebar-nav-btn ${isActive ? 'active' : ''}`}
              onClick={() => onNavigate(item.id)}
              aria-current={isActive ? 'page' : undefined}
            >
              <span className="sidebar-nav-icon">{item.icon}</span>
              <span className="sidebar-nav-label">{item.label}</span>
              {item.badge && <span className="sidebar-nav-badge">{item.badge}</span>}
              {isActive && <span className="sidebar-nav-indicator" />}
            </button>
          );
        })}
      </nav>

      {/* Sidebar Footer Status */}
      <div className="sidebar-footer">
        <div className="sidebar-status-box">
          <div className="sidebar-status-row">
            <span className={`status-dot ${systemHealthy ? 'live' : 'offline'}`} />
            <span className="sidebar-status-text">
              {systemHealthy ? 'Agents Online' : 'Connecting...'}
            </span>
          </div>
          <div className="sidebar-sector-label">
            <ShieldCheck size={11} color="#38bdf8" />
            <span>Kochi Coastal Sector</span>
          </div>
        </div>
        <div className="sidebar-prototype-tag">
          Prototype v0.5 • Decision Support
        </div>
      </div>
    </aside>
  );
};
