import React from "react";
import { LogOut, Menu } from "lucide-react";
import { Company, User } from "../types";

interface HeaderProps {
  currentUser: User | null;
  company: Company | null;
  currentTabName?: string;
  onLogout: () => void;
  onToggleNavigation: () => void;
  navigationOpen: boolean;
  pendingRequestCount: number;
  onResumeRequests: () => void;
}

const pageNames: Record<string, string> = {
  home: "Overview",
  people: "People",
  departments: "Teams",
  roles: "Roles",
  work: "My work",
  files: "Documents",
  assistant: "Ask OracleX",
  approvals: "Requests",
  requests: "Requests",
  notifications: "Notifications",
  activity: "Audit log",
  settings: "Settings"
};

export const Header: React.FC<HeaderProps> = ({
  currentUser,
  company,
  currentTabName = "Workspace",
  onLogout,
  onToggleNavigation,
  navigationOpen, pendingRequestCount, onResumeRequests
}) => {
  const initials = currentUser?.full_name
    ?.split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0].toUpperCase())
    .join("") || "U";

  return (
    <header className="header">
      <div className="header-leading">
        <button
          type="button"
          className="icon-button mobile-menu-button"
          onClick={onToggleNavigation}
          aria-label={navigationOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={navigationOpen}
          aria-controls="primary-navigation"
        >
          <Menu size={18} aria-hidden="true" />
        </button>
        <div className="header-title-wrap">
          <div className="header-eyebrow">{company?.name || "OracleX workspace"}</div>
          <div className="header-title">{pageNames[currentTabName] || currentTabName}</div>
        </div>
      </div>

      <div className="header-actions">
        {pendingRequestCount > 0 && <button type="button" className="btn-secondary pending-request-link" onClick={onResumeRequests}>Unsaved requests <span>{pendingRequestCount}</span></button>}
        <div className="account-summary">
          <div className="account-avatar" aria-hidden="true">{initials}</div>
          <div className="account-text">
            <div className="account-name">{currentUser?.full_name || "User"}</div>
            <div className="account-role">
              {currentUser?.job_title || currentUser?.role?.name || "Member"}
            </div>
          </div>
        </div>

        <button type="button" onClick={onLogout} className="signout-button" aria-label="Sign out">
          <LogOut size={15} aria-hidden="true" />
          <span className="signout-label">Sign out</span>
        </button>
      </div>
    </header>
  );
};
