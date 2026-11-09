import React from "react";

interface NoticeProps {
  tone?: "error" | "success" | "info";
  children: React.ReactNode;
  onDismiss?: () => void;
}

export const Notice: React.FC<NoticeProps> = ({ tone = "info", children, onDismiss }) => (
  <div className={`notice notice-${tone}`} role={tone === "error" ? "alert" : "status"}>
    <span>{children}</span>
    {onDismiss && <button type="button" onClick={onDismiss}>Dismiss</button>}
  </div>
);
