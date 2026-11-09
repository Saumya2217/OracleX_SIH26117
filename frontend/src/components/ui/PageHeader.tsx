import React from "react";

interface PageHeaderProps {
  eyebrow?: string;
  title: string;
  description: string;
  actions?: React.ReactNode;
}

export const PageHeader: React.FC<PageHeaderProps> = ({ eyebrow, title, description, actions }) => (
  <header className="page-header">
    <div>
      {eyebrow && <div className="page-kicker">{eyebrow}</div>}
      <h1>{title}</h1>
      <p>{description}</p>
    </div>
    {actions && <div className="page-header-actions">{actions}</div>}
  </header>
);
