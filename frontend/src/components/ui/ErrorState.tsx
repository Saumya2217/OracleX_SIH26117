import React from "react";

interface ErrorStateProps {
  title: string;
  description: string;
  onRetry: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({ title, description, onRetry }) => <div className="empty-state" role="alert">
  <strong>{title}</strong>
  <p>{description}</p>
  <button type="button" className="btn-secondary" onClick={onRetry}>Try again</button>
</div>;
