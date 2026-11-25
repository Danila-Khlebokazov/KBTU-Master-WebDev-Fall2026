import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { Alert, Spinner, TagChip } from "../components/common";
import { useAction, useApi } from "../hooks";

export const STATUS_LABELS = { todo: "To do", in_progress: "In progress", done: "Done" };

function ProjectForm({ initial = { name: "", description: "" }, submitLabel, onSubmit, onCancel }) {
  const [form, setForm] = useState(initial);
  const { pending, error, run } = useAction();

  const submit = async (e) => {
    e.preventDefault();
    const ok = await run(() =>
      onSubmit({ name: form.name.trim(), description: form.description.trim() || null }),
    );
    if (ok && !onCancel) setForm({ name: "", description: "" });
  };

  return (
    <form className="form" onSubmit={submit}>
      <Alert>{error}</Alert>
      <input
        placeholder="Project name"
        required
        maxLength={255}
        value={form.name}
        onChange={(e) => setForm({ ...form, name: e.target.value })}
      />
      <textarea
        placeholder="Description (optional)"
        rows={2}
        maxLength={5000}
        value={form.description ?? ""}
        onChange={(e) => setForm({ ...form, description: e.target.value })}
      />
      <div className="row">
        <button className="btn btn-sm" disabled={pending}>
          {pending ? "Saving..." : submitLabel}
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

function ProjectCard({ project, onChanged, onDeleted }) {
  const [editing, setEditing] = useState(false);
  const { pending, error, run } = useAction();

  const update = async (body) => {
    const saved = await api(`/projects/${project.id}`, { method: "PATCH", body });
    onChanged(saved);
    setEditing(false);
    return saved;
  };

  const remove = async () => {
    if (!window.confirm(`Delete "${project.name}" and all its tasks?`)) return;
    if (await run(() => api(`/projects/${project.id}`, { method: "DELETE" }))) onDeleted(project.id);
  };

  return (
    <article className="card">
      {editing ? (
        <ProjectForm
          initial={{ name: project.name, description: project.description ?? "" }}
          submitLabel="Save"
          onSubmit={update}
          onCancel={() => setEditing(false)}
        />
      ) : (
        <>
          <h3>{project.name}</h3>
          <p className="muted">{project.description || "No description"}</p>
          <Alert>{error}</Alert>
          <div className="row">
            <Link className="btn btn-sm" to={`/projects/${project.id}`}>
              Open board
            </Link>
            <button type="button" className="btn btn-outline btn-sm" onClick={() => setEditing(true)}>
              Edit
            </button>
            <button type="button" className="btn btn-danger btn-sm" disabled={pending} onClick={remove}>
              {pending ? "Deleting..." : "Delete"}
            </button>
          </div>
        </>
      )}
    </article>
  );
}

function AssignedTasks() {
  const { data, setData, loading, error } = useApi(async () => {
    const [tasks, projects] = await Promise.all([api("/me/tasks"), api("/projects?limit=100", { auth: false })]);
    return { tasks, projects: Object.fromEntries(projects.map((p) => [p.id, p])) };
  });
  const action = useAction();

  const changeStatus = async (task, status) => {
    const saved = await action.run(() => api(`/tasks/${task.id}`, { method: "PATCH", body: { status } }));
    if (saved) setData({ ...data, tasks: data.tasks.map((t) => (t.id === saved.id ? saved : t)) });
  };

  return (
    <section>
      <h2>Tasks assigned to me</h2>
      {loading && <Spinner />}
      <Alert>{error || action.error}</Alert>
      {data && data.tasks.length === 0 && <p className="muted">Nothing assigned to you 🎉</p>}
      {data && data.tasks.length > 0 && (
        <table className="table">
          <thead>
            <tr>
              <th>Task</th>
              <th>Project</th>
              <th>Tags</th>
              <th>Due</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {data.tasks.map((t) => (
              <tr key={t.id}>
                <td>{t.title}</td>
                <td>
                  <Link to={`/projects/${t.project_id}`}>{data.projects[t.project_id]?.name ?? `#${t.project_id}`}</Link>
                </td>
                <td>
                  {t.tags.map((tag) => (
                    <TagChip key={tag.id} tag={tag} />
                  ))}
                </td>
                <td>{t.due_date ?? "—"}</td>
                <td>
                  <select value={t.status} disabled={action.pending} onChange={(e) => changeStatus(t, e.target.value)}>
                    {Object.entries(STATUS_LABELS).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}

export default function MyProjects() {
  const { data: projects, setData, loading, error, reload } = useApi(() => api("/me/projects"));

  const create = async (body) => {
    const created = await api("/projects", { method: "POST", body });
    setData([...(projects ?? []), created]);
    return created;
  };

  return (
    <>
      <h1>My projects</h1>
      <div className="grid">
        <article className="card card-new">
          <h3>New project</h3>
          <ProjectForm submitLabel="Create project" onSubmit={create} />
        </article>
        {loading && <Spinner />}
        {error && (
          <Alert>
            {error}{" "}
            <button type="button" className="link" onClick={reload}>
              Retry
            </button>
          </Alert>
        )}
        {projects?.map((p) => (
          <ProjectCard
            key={p.id}
            project={p}
            onChanged={(saved) => setData(projects.map((x) => (x.id === saved.id ? saved : x)))}
            onDeleted={(id) => setData(projects.filter((x) => x.id !== id))}
          />
        ))}
      </div>
      <AssignedTasks />
    </>
  );
}
