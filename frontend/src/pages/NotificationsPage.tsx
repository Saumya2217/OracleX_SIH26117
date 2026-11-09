import React, { useEffect, useRef, useState } from "react";
import { api } from "../services/api";
import type { InternalNotification } from "../types";
import { notificationDate, notificationRequestId } from "../services/notifications";
import { PageHeader } from "../components/ui/PageHeader";
import { Notice } from "../components/ui/Notice";
import { ErrorState } from "../components/ui/ErrorState";
import { EmptyState } from "../components/ui/EmptyState";

const PAGE_SIZE = 25;
type Cursor = { created_at: string; id: string };

export function NotificationsPage({ onOpenRequest }: { onOpenRequest: (id: string) => void }) {
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [revision, setRevision] = useState(0);
  const [items, setItems] = useState<InternalNotification[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<{ error: boolean; text: string } | null>(null);
  const [hasMore, setHasMore] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [marking, setMarking] = useState<string | null>(null);
  const cursor = useRef<Cursor | undefined>(undefined);
  const moreController = useRef<AbortController | null>(null);
  const readController = useRef<AbortController | null>(null);
  const generation = useRef(0);
  const feedbackRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const controller = new AbortController();
    const currentGeneration = ++generation.current;
    void api.getNotifications(unreadOnly, controller.signal, undefined, PAGE_SIZE).then((page) => {
      if (controller.signal.aborted || generation.current !== currentGeneration) return;
      setItems(page); setError(null); setHasMore(page.length === PAGE_SIZE); cursor.current = page.at(-1);
    }).catch((cause: unknown) => {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "Notifications could not be loaded.");
    });
    return () => { controller.abort(); moreController.current?.abort(); readController.current?.abort(); };
  }, [unreadOnly, revision]);

  const reload = (nextFilter = unreadOnly) => {
    generation.current++;
    moreController.current?.abort(); readController.current?.abort();
    setItems(null); setError(null); setFeedback(null); setLoadingMore(false); setMarking(null);
    cursor.current = undefined; setUnreadOnly(nextFilter); setRevision((value) => value + 1);
  };
  const loadMore = async () => {
    if (loadingMore || marking || !hasMore || !cursor.current) return;
    const currentGeneration = generation.current;
    const controller = new AbortController(); moreController.current = controller;
    setLoadingMore(true); setFeedback(null);
    try {
      const page = await api.getNotifications(unreadOnly, controller.signal, cursor.current, PAGE_SIZE);
      if (controller.signal.aborted || generation.current !== currentGeneration) return;
      setItems((current) => {
        const seen = new Set(current?.map((item) => item.id));
        return [...(current ?? []), ...page.filter((item) => !seen.has(item.id))];
      });
      setHasMore(page.length === PAGE_SIZE); if (page.length) cursor.current = page.at(-1);
    } catch (cause: unknown) {
      if (!controller.signal.aborted) setFeedback({ error: true, text: cause instanceof Error ? cause.message : "More notifications could not be loaded. Please retry." });
    } finally { if (generation.current === currentGeneration) setLoadingMore(false); }
  };
  const markRead = async (item: InternalNotification) => {
    if (marking || loadingMore) return;
    const currentGeneration = generation.current;
    const controller = new AbortController(); readController.current = controller;
    setMarking(item.id); setFeedback(null);
    try {
      const updated = await api.markNotificationRead(item.id, controller.signal);
      if (controller.signal.aborted || generation.current !== currentGeneration) return;
      setItems((current) => (current ?? []).flatMap((record) => record.id !== updated.id ? [record] : unreadOnly ? [] : [updated]));
      setFeedback({ error: false, text: "Notification marked as read." });
      window.requestAnimationFrame(() => { if (!controller.signal.aborted) feedbackRef.current?.focus(); });
    } catch (cause: unknown) {
      if (!controller.signal.aborted) setFeedback({ error: true, text: cause instanceof Error ? cause.message : "The notification could not be marked as read. Please retry." });
    } finally { if (generation.current === currentGeneration) setMarking(null); }
  };

  return <div className="professional-page">
    <PageHeader eyebrow="Your workspace" title="Notifications" description="Request assignments, decisions and completion updates sent to you."
      actions={<button className="btn-secondary" type="button" onClick={() => reload()}>Refresh notifications</button>} />
    <div className="request-tabs" role="group" aria-label="Notification view">
      <button type="button" aria-pressed={!unreadOnly} className={!unreadOnly ? "active" : ""} onClick={() => reload(false)}>All notifications</button>
      <button type="button" aria-pressed={unreadOnly} className={unreadOnly ? "active" : ""} onClick={() => reload(true)}>Unread only</button>
    </div>
    <div ref={feedbackRef} tabIndex={-1}>{feedback && <Notice tone={feedback.error ? "error" : "success"} onDismiss={() => setFeedback(null)}>{feedback.text}</Notice>}</div>
    {items === null && (error ? <ErrorState title="Notifications could not be loaded" description={error} onRetry={() => reload()} /> : <div className="loading-state" role="status">Loading notifications…</div>)}
    {items !== null && items.length === 0 && <EmptyState title={unreadOnly ? "No unread notifications loaded" : "No notifications"} description={hasMore ? "Load more to check older notifications." : "New request updates will appear here."} />}
    {items !== null && <><p className="notification-count">{items.length} {items.length === 1 ? "notification" : "notifications"} loaded{hasMore ? " · older records available" : ""}</p><div className="notification-list">{items.map((item) => {
      const requestId = notificationRequestId(item);
      return <article key={item.id} className={`notification-record ${item.read_at ? "" : "is-unread"}`}>
        <div className="notification-meta"><span>{item.read_at ? "Read" : "Unread"}</span><time dateTime={notificationDate(item.created_at).toISOString()}>{notificationDate(item.created_at).toLocaleString()}</time></div>
        <h2>{item.title}</h2><p>{item.body}</p>
        <div className="notification-actions">{requestId && <button type="button" className="btn-secondary" onClick={() => onOpenRequest(requestId)}>Open request<span className="sr-only">: {item.title}</span></button>}
          {!item.read_at && <button type="button" className="btn-secondary" aria-disabled={Boolean(marking || loadingMore)} onClick={() => void markRead(item)}>{marking === item.id ? "Marking read…" : "Mark as read"}<span className="sr-only">: {item.title}</span></button>}</div>
      </article>;
    })}</div>{hasMore && <button type="button" className="btn-secondary" aria-disabled={loadingMore || Boolean(marking)} onClick={() => void loadMore()}>{loadingMore ? "Loading…" : "Load more notifications"}</button>}</>}
  </div>;
}
