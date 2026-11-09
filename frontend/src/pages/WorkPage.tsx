import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Plus, RefreshCw, Search } from "lucide-react";
import { api } from "../services/api";
import { TaskItem, User } from "../types";
import type { ApiSchema } from "../types/openapi.generated";
import { Dialog } from "../components/ui/Dialog";
import { EmptyState } from "../components/ui/EmptyState";
import { ErrorState } from "../components/ui/ErrorState";
import { Notice } from "../components/ui/Notice";
import { PageHeader } from "../components/ui/PageHeader";
import { StatusLabel } from "../components/ui/StatusLabel";

interface WorkPageProps { currentUser: User; }
type TaskStatus = NonNullable<ApiSchema<"TaskUpdate">["status"]>;
type TaskPriority = NonNullable<ApiSchema<"TaskUpdate">["priority"]>;

const statusOptions: TaskStatus[] = ["TODO", "IN_PROGRESS", "REVIEW", "COMPLETED"];

export const WorkPage: React.FC<WorkPageProps> = ({ currentUser }) => {
  const permissions = currentUser.role?.permissions || [];
  const canCreate = currentUser.is_admin || permissions.includes("task:create");
  const canAssign = currentUser.is_admin || permissions.includes("task:assign");
  const canManage = currentUser.is_admin || permissions.includes("task:manage");
  const [tasks, setTasks] = useState<TaskItem[] | null>(null);
  const [people, setPeople] = useState<User[]>([]);
  const [peopleError, setPeopleError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"ALL" | "ACTIVE" | "COMPLETED">("ACTIVE");
  const [query, setQuery] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [title, setTitle] = useState("");
  const [projectName, setProjectName] = useState("");
  const [priority, setPriority] = useState<TaskPriority>("MEDIUM");
  const [description, setDescription] = useState("");
  const [assigneeId, setAssigneeId] = useState(currentUser.id);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const loadTasks = useCallback(async () => {
    setError(null);
    try { const items = await api.getTasks(); setError(null); setTasks(items); }
    catch (cause: unknown) { setError(cause instanceof Error ? cause.message : "Tasks could not be loaded."); }
  }, []);
  const loadPeople = async () => {
    setPeopleError(null);
    try { setPeople((await api.getUsers()).filter((item) => item.is_active !== false)); }
    catch (cause: unknown) { setPeopleError(cause instanceof Error ? cause.message : "The assignee directory could not be loaded."); }
  };

  useEffect(() => {
    let active = true;
    const controller = new AbortController();
    api.getTasks(controller.signal).then((items) => { if (active) setTasks(items); }).catch((cause: unknown) => { if (active) setError(cause instanceof Error ? cause.message : "Tasks could not be loaded."); });
    return () => { active = false; controller.abort(); };
  }, []);
  useEffect(() => {
    if (!canAssign) return;
    let active = true;
    const controller = new AbortController();
    api.getUsers(controller.signal).then((items) => { if (active) { setPeople(items.filter((item) => item.is_active !== false)); setPeopleError(null); } }).catch((cause: unknown) => { if (active) setPeopleError(cause instanceof Error ? cause.message : "The assignee directory could not be loaded."); });
    return () => { active = false; controller.abort(); };
  }, [canAssign]);

  const filtered = useMemo(() => (tasks || []).filter((task) => {
    if (filter === "ACTIVE" && task.status === "COMPLETED") return false;
    if (filter === "COMPLETED" && task.status !== "COMPLETED") return false;
    const needle = query.trim().toLowerCase();
    return !needle || [task.title, task.description, task.project_name, task.assigned_to_name].some((value) => value?.toLowerCase().includes(needle));
  }), [filter, query, tasks]);

  const updateTask = async (task: TaskItem, updates: ApiSchema<"TaskUpdate">) => {
    setBusyId(task.id); setError(null); setSuccess(null);
    try {
      await api.updateTask(task.id, updates);
      setSuccess(`“${task.title}” was updated.`);
      await loadTasks();
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : "The task could not be updated.");
    } finally { setBusyId(null); }
  };

  const createTask = async (event: React.FormEvent) => {
    event.preventDefault();
    if (canAssign && peopleError) return;
    setBusyId("create"); setError(null); setSuccess(null);
    try {
      await api.createTask({
        title: title.trim(), description: description.trim(), project_name: projectName.trim() || "General",
        priority, status: "TODO", assigned_to_id: canAssign ? assigneeId : currentUser.id,
      });
      setShowCreate(false); setTitle(""); setDescription(""); setProjectName(""); setPriority("MEDIUM"); setAssigneeId(currentUser.id);
      setSuccess("Task created.");
      await loadTasks();
    } catch (cause: unknown) {
      setError(cause instanceof Error ? cause.message : "The task could not be created.");
    } finally { setBusyId(null); }
  };

  return <div className="professional-page">
    <PageHeader eyebrow="Work queue" title="My work" description="Track authorized tasks, ownership, priority, and progress."
      actions={<><button type="button" className="btn-secondary" onClick={() => { api.invalidateCache(); void loadTasks(); }}><RefreshCw size={14} /> Refresh</button>{canCreate && <button type="button" className="btn-primary" onClick={() => setShowCreate(true)}><Plus size={15} /> New task</button>}</>} />

    {error && tasks !== null && <Notice tone="error" onDismiss={() => setError(null)}>{error}</Notice>}
    {success && <Notice tone="success" onDismiss={() => setSuccess(null)}>{success}</Notice>}

    <section className="register-panel">
      <div className="register-toolbar">
        <label className="search-field"><Search size={15} aria-hidden="true" /><span className="sr-only">Search tasks</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search tasks, projects, or assignees" /></label>
        <div className="segmented-control" aria-label="Task status filter">
          {(["ACTIVE", "ALL", "COMPLETED"] as const).map((value) => <button type="button" key={value} aria-pressed={filter === value} className={filter === value ? "active" : ""} onClick={() => setFilter(value)}>{value === "ALL" ? "All" : value === "ACTIVE" ? "Active" : "Completed"}</button>)}
        </div>
      </div>

      {tasks === null && (error ? <ErrorState title="Tasks could not be loaded" description={error} onRetry={() => void loadTasks()} /> : <div className="loading-state"><span className="pulse-indicator" /> Loading tasks…</div>)}
      {tasks !== null && filtered.length === 0 && <EmptyState title={query ? "No matching tasks" : "No tasks in this view"} description={query ? "Try a different search or status filter." : "Tasks you create or receive will appear here."} />}
      {tasks !== null && filtered.length > 0 && <div className="data-table-wrap"><table className="data-table work-table">
        <thead><tr><th>Task</th><th>Owner</th><th>Priority</th><th>Status</th><th>Created</th></tr></thead>
        <tbody>{filtered.map((task) => {
          const editable = canManage || task.assigned_to_id === currentUser.id;
          return <tr key={task.id}>
            <td><strong>{task.title}</strong><small>{task.project_name}{task.description ? ` · ${task.description}` : ""}</small></td>
            <td>{task.assigned_to_name || (task.assigned_to_id === currentUser.id ? currentUser.full_name : "Unassigned")}</td>
            <td><span className={`priority-label priority-${task.priority.toLowerCase()}`}>{task.priority.toLowerCase()}</span></td>
            <td>{editable ? <select aria-label={`Status for ${task.title}`} className="table-select" value={task.status} disabled={busyId === task.id} onChange={(event) => void updateTask(task, { status: event.target.value as TaskStatus })}>{statusOptions.map((value) => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select> : <StatusLabel value={task.status} />}</td>
            <td>{new Date(task.created_at).toLocaleDateString()}</td>
          </tr>;
        })}</tbody>
      </table></div>}
    </section>

    {showCreate && <Dialog title="Create task" description="Add a task to the authorized work queue." onClose={() => setShowCreate(false)} footer={<><button type="button" className="btn-secondary" onClick={() => setShowCreate(false)}>Cancel</button><button type="submit" form="create-task-form" className="btn-primary" disabled={busyId === "create" || !title.trim() || Boolean(canAssign && peopleError)}>{busyId === "create" ? "Creating…" : "Create task"}</button></>}>
      {error && <Notice tone="error">{error}</Notice>}
      {canAssign && peopleError && <ErrorState title="Assignees could not be loaded" description={peopleError} onRetry={() => void loadPeople()} />}
      <form id="create-task-form" className="form-stack" onSubmit={createTask}>
        <label>Task title<input className="input-control" value={title} onChange={(event) => setTitle(event.target.value)} required maxLength={200} /></label>
        <label>Project<input className="input-control" value={projectName} onChange={(event) => setProjectName(event.target.value)} placeholder="General" maxLength={160} /></label>
        <div className="form-grid">
          <label>Priority<select className="input-control" value={priority} onChange={(event) => setPriority(event.target.value as TaskPriority)}><option value="LOW">Low</option><option value="MEDIUM">Medium</option><option value="HIGH">High</option><option value="CRITICAL">Critical</option></select></label>
          {canAssign && <label>Assignee<select className="input-control" value={assigneeId} disabled={Boolean(peopleError)} onChange={(event) => setAssigneeId(event.target.value)}>{people.length === 0 && <option value={currentUser.id}>{currentUser.full_name}</option>}{people.map((person) => <option key={person.id} value={person.id}>{person.full_name}</option>)}</select></label>}
        </div>
        <label>Description<textarea className="input-control" rows={4} value={description} onChange={(event) => setDescription(event.target.value)} maxLength={2000} /></label>
      </form>
    </Dialog>}
  </div>;
};
