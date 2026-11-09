import React, { useEffect, useRef, useState } from "react";
import {
  Activity as ActivityIcon,
  Bell,
  Building2,
  CheckCircle,
  CheckSquare,
  FolderClosed,
  Home,
  KeyRound,
  Search,
  Settings as SettingsIcon,
  Shield,
  Users,
  X,
  type LucideIcon
} from "lucide-react";
import { User } from "../types";
import { useModalFocus } from "./ui/useModalFocus";

interface SidebarProps {
  currentUser: User | null;
  currentTab: string;
  onSelectTab: (tab: string) => void;
  pendingApprovalsCount: number;
  isOpen?: boolean;
  onClose?: () => void;
}

type MenuItem = {
  id: string;
  label: string;
  icon: LucideIcon;
  badge?: number;
};

export const Sidebar: React.FC<SidebarProps> = ({
  currentUser,
  currentTab,
  onSelectTab,
  pendingApprovalsCount,
  isOpen = false,
  onClose
}) => {
  const [isMobile, setIsMobile] = useState(() => window.matchMedia("(max-width: 900px)").matches);
  const boundaryRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLElement>(null);
  useEffect(() => {
    const media = window.matchMedia("(max-width: 900px)");
    const onChange = () => setIsMobile(media.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);
  useModalFocus(panelRef, boundaryRef, isMobile && isOpen, () => onClose?.());
  const isAdmin = currentUser?.is_admin === true;
  const permissions = currentUser?.role?.permissions || [];
  const isManager = permissions.includes("workflow:approve") || permissions.includes("task:assign");

  let workspaceItems: MenuItem[];
  let managementItems: MenuItem[] = [];

  if (isAdmin) {
    workspaceItems = [
      { id: "home", label: "Overview", icon: Home },
      { id: "files", label: "Documents", icon: FolderClosed },
      { id: "assistant", label: "Ask OracleX", icon: Search },
      { id: "work", label: "My work", icon: CheckSquare },
      {
        id: "requests",
        label: "Requests",
        icon: CheckCircle,
        badge: pendingApprovalsCount || undefined
      }
    ];
    managementItems = [
      { id: "people", label: "People", icon: Users },
      { id: "departments", label: "Teams", icon: Building2 },
      { id: "roles", label: "Roles", icon: KeyRound },
      { id: "activity", label: "Audit log", icon: ActivityIcon },
      { id: "settings", label: "Settings", icon: SettingsIcon }
    ];
  } else if (isManager) {
    workspaceItems = [
      { id: "home", label: "Overview", icon: Home },
      { id: "files", label: "Documents", icon: FolderClosed },
      { id: "assistant", label: "Ask OracleX", icon: Search },
      { id: "work", label: "My work", icon: CheckSquare },
      {
        id: "requests",
        label: "Requests",
        icon: CheckCircle,
        badge: pendingApprovalsCount || undefined
      }
    ];
    managementItems = [
      { id: "people", label: "People", icon: Users },
      ...(permissions.includes("audit:view") ? [{ id: "activity", label: "Audit log", icon: ActivityIcon }] : [])
    ];
  } else {
    workspaceItems = [
      { id: "home", label: "Overview", icon: Home },
      { id: "files", label: "Documents", icon: FolderClosed },
      { id: "assistant", label: "Ask OracleX", icon: Search },
      { id: "work", label: "My work", icon: CheckSquare },
      { id: "requests", label: "Requests", icon: CheckCircle }
    ];
  }

  const roleTitle = isAdmin ? "Administrator" : isManager ? "Team lead" : "Team member";
  workspaceItems.push({ id: "notifications", label: "Notifications", icon: Bell });

  const renderGroup = (label: string, items: MenuItem[]) => items.length > 0 && (
    <div className="nav-group">
      <div className="nav-group-label">{label}</div>
      {items.map((item) => {
        const Icon = item.icon;
        const isActive = currentTab === item.id;
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onSelectTab(item.id)}
            className={`nav-btn ${isActive ? "active" : ""}`}
            aria-current={isActive ? "page" : undefined}
          >
            <Icon size={17} aria-hidden="true" />
            <span className="nav-btn-label">{item.label}</span>
            {item.badge !== undefined && <span className="nav-btn-badge">{item.badge}</span>}
          </button>
        );
      })}
    </div>
  );

  return (
    <div ref={boundaryRef} className="sidebar-layer">
      {isMobile && isOpen && <button tabIndex={-1} className="sidebar-scrim" onClick={onClose} aria-label="Close navigation" />}
      <aside ref={panelRef} id="primary-navigation" tabIndex={-1} inert={isMobile && !isOpen} className={`sidebar ${isOpen ? "open" : ""}`} role={isMobile && isOpen ? "dialog" : undefined} aria-modal={isMobile && isOpen ? true : undefined} aria-label="Primary navigation">
        <div className="sidebar-brand">
          <div className="brand-mark"><Shield size={17} aria-hidden="true" /></div>
          <div>
            <div className="brand-name">OracleX</div>
            <div className="brand-context">Company workspace</div>
          </div>
          {isMobile && <button type="button" className="icon-button sidebar-close" aria-label="Close navigation" onClick={onClose}><X size={16} aria-hidden="true" /></button>}
        </div>

        <nav className="sidebar-nav">
          {renderGroup("Workspace", workspaceItems)}
          {renderGroup("Administration", managementItems)}
        </nav>

        <div className="sidebar-account">
          <div className="sidebar-account-name">{currentUser?.full_name || "Guest"}</div>
          <div className="sidebar-account-role">{currentUser?.job_title || roleTitle}</div>
        </div>
      </aside>
    </div>
  );
};
