import React, { useCallback, useEffect, useRef, useState } from "react";
import { Archive, Clipboard, FileText, MessageSquarePlus, RotateCcw, Send } from "lucide-react";
import { AgentCitation, ConversationDetail, ConversationSummary, User } from "../types";
import { api } from "../services/api";

interface AIAssistantPageProps {
  user: User | null;
  initialPrompt?: string;
  initialConversationId?: string;
  onConversationChange?: (conversationId?: string) => void;
  onNavigateToRequests: (requestId?: string) => void;
}

const formatTime = (value: string) => new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
const readableMode = (value: string) => value.replaceAll("_", " ").toLowerCase().replace(/^./, (letter) => letter.toUpperCase());

export const AIAssistantPage: React.FC<AIAssistantPageProps> = ({ initialPrompt, initialConversationId, onConversationChange, onNavigateToRequests }) => {
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [conversation, setConversation] = useState<ConversationDetail | null>(null);
  const [inputText, setInputText] = useState(initialPrompt || "");
  const [isLoading, setIsLoading] = useState(false);
  const [isHistoryLoading, setIsHistoryLoading] = useState(true);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [isConversationLoading, setIsConversationLoading] = useState(false);
  const [isArchiving, setIsArchiving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const detailController = useRef<AbortController | null>(null);
  useEffect(() => () => detailController.current?.abort(), []);

  const loadConversation = useCallback(async (id: string) => {
    detailController.current?.abort();
    const controller = new AbortController();
    detailController.current = controller;
    setIsConversationLoading(true);
    setError(null);
    try {
      const detail = await api.getConversation(id, controller.signal);
      if (controller.signal.aborted) return;
      setConversation(detail);
      setSelectedId(id);
      onConversationChange?.(id);
    } catch (cause: unknown) {
      if (!controller.signal.aborted) setError(cause instanceof Error ? cause.message : "This conversation could not be opened.");
    } finally {
      if (detailController.current === controller) { detailController.current = null; setIsConversationLoading(false); }
    }
  }, [onConversationChange]);

  const retryHistory = async () => {
    setIsHistoryLoading(true);
    setHistoryError(null);
    try {
      setConversations(await api.getConversations());
      if (initialConversationId) await loadConversation(initialConversationId);
    } catch (cause: unknown) {
      setHistoryError(cause instanceof Error ? cause.message : "Conversation history could not be loaded.");
    } finally { setIsHistoryLoading(false); }
  };

  const refreshHistory = useCallback(async (preferredId?: string) => {
    const items = await api.getConversations();
    setConversations(items);
    const target = preferredId || selectedId;
    if (target) await loadConversation(target);
    else setConversation(null);
  }, [loadConversation, selectedId]);

  useEffect(() => {
    let active = true;
    let historyFetched = false;
    const controller = new AbortController();
    api.getConversations(false, controller.signal)
      .then(async (items) => {
        if (!active) return;
        historyFetched = true;
        setConversations(items);
        if (initialConversationId) {
          const detail = await api.getConversation(initialConversationId, controller.signal);
          if (active) {
            setConversation(detail);
            setSelectedId(detail.id);
          }
        } else if (active) {
          setConversation(null);
          setSelectedId(null);
        }
      })
      .catch((cause: unknown) => {
        if (!active) return;
        const message = cause instanceof Error ? cause.message : "Conversation history could not be loaded.";
        if (historyFetched) setError(message);
        else setHistoryError(message);
      })
      .finally(() => active && setIsHistoryLoading(false));
    return () => { active = false; controller.abort(); };
  }, [initialConversationId]);

  useEffect(() => {
    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    messagesEndRef.current?.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth" });
  }, [conversation?.messages, isLoading]);

  const handleSend = async (overrideText?: string) => {
    const message = (overrideText || inputText).trim();
    if (!message || isLoading || isArchiving || isConversationLoading || (initialConversationId && !conversation) || conversation?.status === "ARCHIVED") return;
    setInputText("");
    setError(null);
    setIsLoading(true);
    try {
      const response = await api.queryAgent(message, selectedId || undefined);
      await refreshHistory(response.conversation_id);
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : "OracleX could not complete this request.");
      await refreshHistory().catch(() => undefined);
    } finally {
      setIsLoading(false);
    }
  };

  const openSource = async (citation: AgentCitation) => {
    try {
      setError(null);
      await api.downloadDocumentVersion(citation.document_id, citation.version_id, citation.filename);
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : "The retained source could not be opened.");
    }
  };

  const archiveConversation = async () => {
    if (!conversation || isArchiving) return;
    setIsArchiving(true);
    setError(null);
    try {
      await api.updateConversation(conversation.id, { status: "ARCHIVED" });
      setConversations((items) => items.filter((item) => item.id !== conversation.id));
      setSelectedId(null);
      setConversation(null);
      onConversationChange?.();
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : "This conversation could not be archived.");
    } finally { setIsArchiving(false); }
  };

  const copyMessage = async (content: string) => {
    try { await navigator.clipboard.writeText(content); }
    catch { setError("The browser could not copy this message. Select the text and copy it manually."); }
  };
  const conversationPending = isConversationLoading || Boolean(initialConversationId && !conversation);
  const startNewConversation = () => {
    detailController.current?.abort();
    setIsConversationLoading(false);
    setSelectedId(null); setConversation(null); setError(null); setInputText("");
    onConversationChange?.();
  };

  const retryFailedMessage = (sequence: number) => {
    const prior = conversation?.messages.find((message) => message.sequence === sequence - 1 && message.role === "USER");
    if (prior) void handleSend(prior.content);
  };

  const starterPrompts = [
    "What is the company annual leave and sick leave policy?",
    "What are the sprint milestones in the Q4 product roadmap?",
    "What is our customer support SLA commitment?"
  ];

  return (
    <div className="assistant-workspace">
      <aside className="conversation-rail" aria-label="Conversation history">
        <button
          type="button"
          className="new-conversation-button"
          disabled={isLoading || isArchiving}
          onClick={startNewConversation}
        >
          <MessageSquarePlus size={15} /> New conversation
        </button>
        <div className="conversation-rail-label">Recent</div>
        <div className="conversation-list">
          {isHistoryLoading && <div className="rail-empty">Loading history…</div>}
          {!isHistoryLoading && historyError && <div className="rail-empty" role="alert"><p>{historyError}</p><button type="button" className="btn-secondary compact" onClick={() => void retryHistory()}>Try again</button></div>}
          {!isHistoryLoading && !historyError && conversations.length === 0 && <div className="rail-empty">No saved conversations yet.</div>}
          {conversations.map((item) => (
            <button
              type="button"
              key={item.id}
              disabled={isLoading || isArchiving}
              className={`conversation-row ${selectedId === item.id ? "active" : ""}`}
              onClick={() => void loadConversation(item.id)}
            >
              <strong>{item.title}</strong>
              <span>{new Date(item.last_message_at).toLocaleDateString()} · Level {item.classification_level}</span>
            </button>
          ))}
        </div>
      </aside>

      <section className="assistant-panel">
        <header className="assistant-panel-header">
          <div>
            <h1>{conversation?.title || "Ask OracleX"}</h1>
            <p>Saved answers from company evidence, with exact retained sources.</p>
          </div>
          {conversation && (
            <button type="button" disabled={isLoading || isConversationLoading || isArchiving} className="btn-secondary compact" onClick={() => void archiveConversation()}>
              <Archive size={13} /> {isArchiving ? "Archiving…" : "Archive"}
            </button>
          )}
        </header>

        <div className="mobile-conversation-controls">
          <label>Saved conversations
            <select aria-label="Saved conversations" className="input-control" value={selectedId || ""} disabled={isHistoryLoading || isLoading || isArchiving} onChange={(event) => {
              if (event.target.value) void loadConversation(event.target.value);
              else startNewConversation();
            }}>
              <option value="">New conversation</option>
              {conversations.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}
            </select>
          </label>
          <button type="button" className="btn-secondary compact" disabled={isLoading || isArchiving} onClick={startNewConversation}>New conversation</button>
          {historyError && <div className="mobile-history-error" role="alert"><p>{historyError}</p><button type="button" className="btn-secondary compact" disabled={isHistoryLoading} onClick={() => void retryHistory()}>Try again</button></div>}
        </div>
        <div className="assistant-transcript" aria-live="polite">
          {!conversation && !isLoading && !conversationPending && (
            <div className="assistant-empty">
              <h2>Start with a company question</h2>
              <p>Your conversation, evidence references, and failed runs are saved to your account.</p>
              <div className="assistant-starters">
                {starterPrompts.map((prompt) => (
                  <button key={prompt} type="button" onClick={() => void handleSend(prompt)}>{prompt}</button>
                ))}
              </div>
            </div>
          )}

          {conversation?.messages.map((message) => {
            const run = message.run;
            return (
              <article key={message.id} className={`assistant-message ${message.role === "USER" ? "from-user" : "from-assistant"}`}>
                <div className="message-meta">
                  <strong>{message.role === "USER" ? "You" : "OracleX"}</strong>
                  <span>{formatTime(message.created_at)}</span>
                </div>
                <div className="message-body">
                  <p>{message.content}</p>
                  {run && (
                    <div className="run-metadata">
                      <span className={`evidence-chip evidence-${(run.evidence_status || run.status).toLowerCase()}`}>
                        {run.status === "FAILED" ? "Saved failure" : (run.evidence_status || "Completed").replaceAll("_", " ")}
                      </span>
                      {run.generation_mode && <span>{readableMode(run.generation_mode)} · {run.model_id || "no model"} · {run.retrieval_mode || "no retrieval"}</span>}
                    </div>
                  )}
                  {run?.safe_error_message && <div className="inline-error">{run.safe_error_message}</div>}
                  {run?.citations && run.citations.length > 0 && (
                    <div className="answer-citations">
                      <div className="citation-heading"><FileText size={12} /> Evidence used</div>
                      {run.citations.map((citation, index) => (
                        <div key={`${citation.chunk_id}-${index}`} className="answer-citation">
                          <div><strong>[{index + 1}] {citation.title}</strong><span>{citation.location_label}</span></div>
                          <p>{citation.excerpt}</p>
                          <button type="button" onClick={() => void openSource(citation)}>Download retained source</button>
                        </div>
                      ))}
                    </div>
                  )}
                  {message.role === "ASSISTANT" && (
                    <div className="message-actions">
                      <button type="button" onClick={() => void copyMessage(message.content)}><Clipboard size={12} /> Copy</button>
                      {run?.status === "FAILED" && <button type="button" onClick={() => retryFailedMessage(message.sequence)}><RotateCcw size={12} /> Retry</button>}
                      {run?.business_request_id && <button type="button" onClick={() => onNavigateToRequests(run.business_request_id ?? undefined)}>Open request</button>}
                    </div>
                  )}
                </div>
              </article>
            );
          })}

          {isLoading && <div className="assistant-loading"><span className="pulse-indicator" /> Working with authorized company records…</div>}
          {conversationPending && !error && <div className="assistant-loading" role="status">Loading conversation…</div>}
          <div ref={messagesEndRef} />
        </div>

        {error && <div className="assistant-source-error" role="alert">{error}</div>}
        <form className="assistant-composer" onSubmit={(event) => { event.preventDefault(); void handleSend(); }}>
          <textarea
            aria-label="Message to OracleX"
            value={inputText}
            onChange={(event) => setInputText(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                event.preventDefault();
                void handleSend();
              }
            }}
            placeholder="Ask a question or describe a controlled request…"
            disabled={isLoading || isArchiving || conversationPending || conversation?.status === "ARCHIVED"}
            rows={2}
          />
          <button type="submit" className="btn-primary" disabled={isLoading || isArchiving || conversationPending || !inputText.trim()}><Send size={14} /> Send</button>
        </form>
      </section>
    </div>
  );
};
