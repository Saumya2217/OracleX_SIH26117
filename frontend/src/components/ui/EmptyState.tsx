import React from "react";
import { Inbox } from "lucide-react";

interface EmptyStateProps {
  title: string;
  description: string;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({ title, description, action }) => (
  <div className="blank-state">
    <Inbox size={24} aria-hidden="true" />
    <strong>{title}</strong>
    <p>{description}</p>
    {action}
  </div>
);
