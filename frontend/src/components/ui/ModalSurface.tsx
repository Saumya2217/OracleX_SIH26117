import React, { useRef } from "react";
import { useModalFocus } from "./useModalFocus";

interface ModalSurfaceProps {
  labelledBy: string;
  className?: string;
  onClose: () => void;
  dismissible?: boolean;
  children: React.ReactNode;
}

export const ModalSurface: React.FC<ModalSurfaceProps> = ({ labelledBy, className = "", onClose, dismissible = true, children }) => {
  const boundaryRef = useRef<HTMLDivElement>(null);
  const panelRef = useRef<HTMLElement>(null);
  useModalFocus(panelRef, boundaryRef, true, onClose, dismissible);
  return <div ref={boundaryRef} className="modal-backdrop" onMouseDown={(event) => {
    if (dismissible && event.currentTarget === event.target) onClose();
  }}>
    <section ref={panelRef} tabIndex={-1} className={`modal-panel ${className}`} role="dialog" aria-modal="true" aria-labelledby={labelledBy}>
      {children}
    </section>
  </div>;
};
