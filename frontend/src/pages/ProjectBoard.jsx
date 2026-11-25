import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../AuthContext";
import { Alert, Spinner, TagChip } from "../components/common";
import { useAction, useApi } from "../hooks";
import { STATUS_LABELS } from "./MyProjects";

const STATUSES = Object.keys(STATUS_LABELS);

const toForm = (t) => ({
  title: t?.title ?? "",
  description: t?.description ?? "",
  status: t?.status ?? "todo",
  priority: t?.priority ?? 3,
  due_date: t?.due_date ?? "",
  assignee_id: t?.assignee_id ?? "",
  tag_ids: t?.tags.map((tag) => tag.id) ?? [],
});

const toBody = (f) => ({
  title: f.title.trim(),
  description: f.description.trim() || null,
  status: f.status,
  priority: Number(f.priority),
  due_date: f.due_date || null,
  assignee_id: f.assignee_id === "" ? null : Number(f.assignee_id),
  tag_ids: f.tag_ids,
});

function TaskForm({ task, users, tags, onSubmit, onCancel }) {
  const [form, setForm] = useState(toForm(task));
  const { pending, error, run } = useAction();
  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });
  const toggleTag = (id) =>
    setForm({
      ...form,
      tag_ids: form.tag_ids.includes(id) ? form.tag_ids.filter((x) => x !== id) : [...form.tag_ids, id],
    });

  const submit = async (e) => {
    e.preventDefault();
    const ok = await run(() => onSubmit(toBody(form)));
    if (ok && !task) setForm(toForm(null));
  };

  return (
    <form className="form task-form" onSubmit={submit}>
      <Alert>{error}</Alert>
      <input placeholder="Task title" required maxLength={255} value={form.title} onChange={set("title")} />
      <textarea placeholder="Description" rows={2} maxLength={5000} value={form.description} onChange={set("description")} />
      <div className="row wrap">
        <label className="inline">
          Status
          <select value={form.status} onChange={set("status")}>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {STATUS_LABELS[s]}
              </option>
            ))}
          </select>
        </label>
        <label className="inline">
          Priority
          <select value={form.priority} onChange={set("priority")}>
            {[1, 2, 3, 4, 5].map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        <label className="inline">
          Due
          <input type="date" value={form.due_date} onChange={set("due_date")} />
        </label>
        <label className="inline">
          Assignee
          <select value={form.assignee_id} onChange={set("assignee_id")}>
            <option value="">— nobody —</option>
            {users.map((u) => (
              <option key={u.id} value={u.id}>
                {u.name} (@{u.username})
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="tag-picker">
        {tags.map((tag) => (
          <label key={tag.id} className={`tag-option ${form.tag_ids.includes(tag.id) ? "selected" : ""}`}>
            <input type="checkbox" checked={form.tag_ids.includes(tag.id)} onChange={() => toggleTag(tag.id)} />
            <TagChip tag={tag} />
          </label>
        ))}
        {tags.length === 0 && (
          <span className="muted small">
            No tags yet — <Link to="/tags">create some</Link>
          </span>
        )}
      </div>
      <div className="row">
        <button className="btn btn-sm" disabled={pending}>
          {pending ? "Saving..." : task ? "Save task" : "Add task"}
        </button>
        {onCancel && (
          <button type="button" className="btn btn-outline btn-sm" onClick={onCancel}>
            Cancel
          </button>
        )}
      </div>
    </form>
  );
}

function TaskCard({ task, users, tags, canEdit, canDelete, onSaved, onDeleted }) {
  const [editing, setEditing] = useState(false);
  const { pending, error, run } = useAction();
  const assignee = users.find((u) => u.id === task.assignee_id);
  const idx = STATUSES.indexOf(task.status);

  const move = async (status) => {
    const saved = await run(() => api(`/tasks/${task.id}`, { method: "PATCH", body: { status } }));
    if (saved) onSaved(saved);
  };

  const remove = async () => {
    if (!window.confirm(`Delete task "${task.title}"?`)) return;
    if (await run(() => api(`/tasks/${task.id}`, { method: "DELETE" }))) onDeleted(task.id);
  };

  if (editing) {
    return (
      <div className="task editing">
        <TaskForm
          task={task}
          users={users}
          tags={tags}
          onCancel={() => setEditing(false)}
          onSubmit={async (body) => {
            const saved = await api(`/tasks/${task.id}`, { method: "PUT", body });
            onSaved(saved);
            setEditing(false);
            return saved;
          }}
        />
      </div>
    );
  }

  return (
    <div className={`task priority-${task.priority}`}>
      <div className="task-title">{task.title}</div>
      {task.description && <div className="small muted">{task.description}</div>}
      <div className="task-meta small">
        <span title="Priority">P{task.priority}</span>
        {task.due_date && <span>📅 {task.due_date}</span>}
        <span>👤 {assignee ? assignee.name : "unassigned"}</span>
      </div>
      <div>
        {task.tags.map((tag) => (
          <TagChip key={tag.id} tag={tag} />
        ))}
      </div>
      <Alert>{error}</Alert>
      {canEdit && (
        <div className="row task-actions">
          <button type="button" className="btn btn-outline btn-xs" disabled={pending || idx === 0} onClick={() => move(STATUSES[idx - 1])}>
            ←
          </button>
          <button
            type="button"
            className="btn btn-outline btn-xs"
            disabled={pending || idx === STATUSES.length - 1}
            onClick={() => move(STATUSES[idx + 1])}
          >
            →
          </button>
          <button type="button" className="btn btn-outline btn-xs" onClick={() => setEditing(true)}>
            Edit
          </button>
          {canDelete && (
            <button type="button" className="btn btn-danger btn-xs" disabled={pending} onClick={remove}>
              Delete
            </button>
          )}
        </div>
      )}
    </div>
  );
}

export default function ProjectBoard() {
  const { projectId } = useParams();
  const { user } = useAuth();
  const { data, setData, loading, error, reload } = useApi(async () => {
    const [project, tasks, tags, users] = await Promise.all([
      api(`/projects/${projectId}`, { auth: false }),
      api(`/projects/${projectId}/tasks`, { auth: false }),
      api("/tags", { auth: false }),
      api("/users?limit=100", { auth: false }),
    ]);
    return { project, tasks, tags, users };
  }, [projectId]);

  if (loading) return <Spinner label="Loading board..." />;
  if (error)
    return (
      <Alert>
        {error}{" "}
        <button type="button" className="link" onClick={reload}>
          Retry
        </button>
      </Alert>
    );

  const { project, tasks, tags, users } = data;
  const isOwner = project.owner_id === user.id;
  const setTasks = (next) => setData({ ...data, tasks: next });
  const onSaved = (saved) => setTasks(tasks.map((t) => (t.id === saved.id ? saved : t)));
  const onDeleted = (id) => setTasks(tasks.filter((t) => t.id !== id));

  const create = async (body) => {
    const created = await api(`/projects/${project.id}/tasks`, { method: "POST", body });
    setTasks([...tasks, created]);
    return created;
  };

  return (
    <>
      <p className="small">
        <Link to={isOwner ? "/my-projects" : "/"}>← Back</Link>
      </p>
      <h1>{project.name}</h1>
      <p className="muted">
        {project.description || "No description"} · owner <b>{project.owner.name}</b> · {tasks.length} tasks
      </p>
      {!isOwner && (
        <Alert type="info">
          You are viewing someone else&apos;s project. You can only edit tasks assigned to you.
        </Alert>
      )}

      {isOwner && (
        <details className="card">
          <summary>
            <b>+ New task</b>
          </summary>
          <TaskForm users={users} tags={tags} onSubmit={create} />
        </details>
      )}

      <div className="board">
        {STATUSES.map((status) => {
          const column = tasks.filter((t) => t.status === status);
          return (
            <section key={status} className="column">
              <h3>
                {STATUS_LABELS[status]} <span className="badge">{column.length}</span>
              </h3>
              {column.map((t) => (
                <TaskCard
                  key={t.id}
                  task={t}
                  users={users}
                  tags={tags}
                  canEdit={isOwner || t.assignee_id === user.id}
                  canDelete={isOwner}
                  onSaved={onSaved}
                  onDeleted={onDeleted}
                />
              ))}
              {column.length === 0 && <p className="muted small">No tasks</p>}
            </section>
          );
        })}
      </div>
    </>
  );
}
