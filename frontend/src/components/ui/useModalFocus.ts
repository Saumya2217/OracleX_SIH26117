import { useEffect, useRef, type RefObject } from "react";

const focusableSelector = 'button:not(:disabled), input:not(:disabled):not([type="hidden"]), select:not(:disabled), textarea:not(:disabled), a[href], summary, [tabindex]:not([tabindex="-1"])';

export function useModalFocus(
  panelRef: RefObject<HTMLElement | null>,
  boundaryRef: RefObject<HTMLElement | null>,
  enabled: boolean,
  onClose: () => void,
  dismissible = true,
): void {
  const closeRef = useRef(onClose);
  const dismissibleRef = useRef(dismissible);
  useEffect(() => { closeRef.current = onClose; dismissibleRef.current = dismissible; }, [onClose, dismissible]);

  useEffect(() => {
    const panel = panelRef.current;
    const boundary = boundaryRef.current;
    if (!enabled || !panel || !boundary) return;
    const priorFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const priorOverflow = document.body.style.overflow;
    const blocked = new Map<HTMLElement, boolean>();
    let branch: HTMLElement = boundary;
    while (branch.parentElement) {
      for (const sibling of branch.parentElement.children) {
        if (sibling instanceof HTMLElement && sibling !== branch) {
          blocked.set(sibling, sibling.inert);
          sibling.setAttribute("inert", "");
        }
      }
      if (branch.parentElement === document.body) break;
      branch = branch.parentElement;
    }
    document.body.style.overflow = "hidden";
    const controls = () => Array.from(panel.querySelectorAll<HTMLElement>(focusableSelector))
      .filter((element) => element.getClientRects().length > 0 && !element.closest("[inert]"));
    const focusFirst = () => (controls()[0] || panel).focus();
    focusFirst();
    const onFocus = (event: FocusEvent) => {
      if (event.target instanceof Node && !panel.contains(event.target)) focusFirst();
    };
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape" && dismissibleRef.current) {
        event.preventDefault();
        event.stopPropagation();
        closeRef.current();
      }
      if (event.key !== "Tab") return;
      const items = controls();
      const first = items[0];
      const last = items.at(-1);
      if (!first || !last) { event.preventDefault(); panel.focus(); return; }
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
    };
    document.addEventListener("focusin", onFocus);
    document.addEventListener("keydown", onKey);
    // Submitting can disable or remove the focused action without a focusin event.
    const observer = new MutationObserver(() => {
      if (document.activeElement === document.body) focusFirst();
    });
    observer.observe(panel, { childList: true, subtree: true, attributes: true, attributeFilter: ["disabled"] });
    return () => {
      observer.disconnect();
      document.removeEventListener("focusin", onFocus);
      document.removeEventListener("keydown", onKey);
      for (const [element, priorInert] of blocked) element.toggleAttribute("inert", priorInert);
      document.body.style.overflow = priorOverflow;
      if (priorFocus?.isConnected && !priorFocus.closest("[inert]")) priorFocus.focus();
      else window.requestAnimationFrame(() => {
        const heading = document.querySelector<HTMLElement>("#main-content h1");
        if (heading) { heading.tabIndex = -1; heading.focus(); }
      });
    };
  }, [enabled, panelRef, boundaryRef]);
}
