import React, { useEffect, useState } from "react";
import { Cpu, RefreshCw, Server } from "lucide-react";
import { api } from "../services/api";
import { ErrorState } from "../components/ui/ErrorState";
import { PageHeader } from "../components/ui/PageHeader";
import type { ApiSchema } from "../types/openapi.generated";

type ModelHealth = ApiSchema<"AgentHealthResponse">;

export const SettingsPage: React.FC = () => {
  const [modelHealth, setModelHealth] = useState<ModelHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const checkHealth = async () => {
    setLoading(true);
    setError(null);
    try { setModelHealth(await api.getAiHealth()); }
    catch (cause: unknown) { setError(cause instanceof Error ? cause.message : "Model status could not be loaded."); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    api.getAiHealth(controller.signal)
      .then((data) => { if (active) setModelHealth(data); })
      .catch((cause: unknown) => { if (active) setError(cause instanceof Error ? cause.message : "Model status could not be loaded."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; controller.abort(); };
  }, []);

  const status = modelHealth?.status;
  const statusLabel = status === "online" ? "Available" : status === "model_missing" ? "Model import required" : status === "simulated" ? "Demo simulator" : "Unavailable";
  const statusClass = status === "online" ? "badge-public" : status === "unavailable" ? "badge-restricted" : "badge-confidential";

  return <div className="professional-page">
    <PageHeader eyebrow="Operations" title="System status" description="Measured local model connectivity and installed model inventory."
      actions={<button type="button" onClick={() => void checkHealth()} disabled={loading} className="btn-secondary"><RefreshCw size={15} aria-hidden="true" /> {loading ? "Checking…" : "Refresh status"}</button>} />

    {loading && !modelHealth && <div className="loading-state"><span className="pulse-indicator" /> Checking model runtime…</div>}
    {error && <ErrorState title="Model status is unknown" description={error} onRetry={() => void checkHealth()} />}
    {modelHealth && !error && <>
      <div className="system-status-grid">
        <section className="card" aria-labelledby="model-runtime-title">
          <div className="section-heading"><Cpu size={19} aria-hidden="true" /><h2 id="model-runtime-title">Model runtime</h2></div>
          <dl className="detail-list">
            <div><dt>Status</dt><dd><span className={`badge ${statusClass}`}>{statusLabel}</span></dd></div>
            <div><dt>Provider</dt><dd>{modelHealth.provider || "Not reported"}</dd></div>
            <div><dt>Engine</dt><dd>{modelHealth.engine || "Not reported"}</dd></div>
            <div><dt>Active model</dt><dd className="mono">{modelHealth.active_model || "None"}</dd></div>
          </dl>
        </section>
        <section className="card" aria-labelledby="installed-models-title">
          <div className="section-heading"><Server size={19} aria-hidden="true" /><h2 id="installed-models-title">Installed models</h2></div>
          {modelHealth.available_models?.length ? <ul className="plain-list">{modelHealth.available_models.map((model) => <li key={model} className="mono">{model}</li>)}</ul>
            : <p className="empty-copy">{status === "unavailable" ? "The configured runtime could not be reached, so its model inventory is unknown." : status === "model_missing" ? modelHealth.message || "The configured model is not installed." : "No installed models were reported."}</p>}
        </section>
      </div>
      <section className="card system-note" aria-labelledby="deployment-note-title">
        <h2 id="deployment-note-title">Deployment note</h2>
        <p>This page reports model connectivity only. Network isolation, backup status, database readiness, and compliance require separate operational checks on the deployed environment.</p>
      </section>
    </>}
  </div>;
};
