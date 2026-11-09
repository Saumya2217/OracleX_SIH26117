import React, { useId } from "react";
import { X } from "lucide-react";
import { ModalSurface } from "./ModalSurface";

interface DialogProps {
  title: string;
  description?: string;
  onClose: () => void;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

export const Dialog: React.FC<DialogProps> = ({ title, description, onClose, children, footer }) => {
  const titleId = useId();

  return (
    <ModalSurface className="professional-dialog" labelledBy={titleId} onClose={onClose}>
        <header className="dialog-header">
          <div><h2 id={titleId}>{title}</h2>{description && <p>{description}</p>}</div>
          <button type="button" className="icon-button" onClick={onClose} aria-label="Close dialog"><X size={16} /></button>
        </header>
        <div className="dialog-body">{children}</div>
        {footer && <footer className="dialog-footer">{footer}</footer>}
    </ModalSurface>
  );
};
