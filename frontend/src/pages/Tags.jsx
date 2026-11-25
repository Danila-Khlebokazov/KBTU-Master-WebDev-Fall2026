import { useState } from "react";
import { api } from "../api";
import { Alert, Spinner, TagChip } from "../components/common";
import { useAction, useApi } from "../hooks";

function TagRow({ tag, onSaved, onDeleted }) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({ name: tag.name, color: tag.color });
  const { pending, error, run } = useAction();

  const save = async (e) => {
    e.preventDefault();
    const saved = await run(() => api(`/tags/${tag.id}`, { method: "PUT", body: form }));
    if (saved) {
      onSaved(saved);
      setEditing(false);
    }
  };

  const remove = async () => {
    if (!window.confirm(`Delete tag "${tag.name}"? It will be removed from all tasks.`)) return;
    if (await run(() => api(`/tags/${tag.id}`, { method: "DELETE" }))) onDeleted(tag.id);
  };

  return (
    <li className="tag-row">
      {editing ? (
        <form className="row" onSubmit={save}>
          <input required maxLength={50} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input type="color" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} />
          <button className="btn btn-sm" disabled={pending}>
            {pending ? "Saving..." : "Save"}
          </button>
          <button type="button" className="btn btn-outline btn-sm" onClick={() => setEditing(false)}>
            Cancel
          </button>
        </form>
      ) : (
        <div className="row">
          <TagChip tag={tag} />
          <span className="spacer" />
          <button type="button" className="btn btn-outline btn-sm" onClick={() => setEditing(true)}>
            Edit
          </button>
          <button type="button" className="btn btn-danger btn-sm" disabled={pending} onClick={remove}>
            Delete
          </button>
        </div>
      )}
      <Alert>{error}</Alert>
    </li>
  );
}

export default function Tags() {
  const { data: tags, setData, loading, error } = useApi(() => api("/tags", { auth: false }));
  const [form, setForm] = useState({ name: "", color: "#3b82f6" });
  const action = useAction();

  const create = async (e) => {
    e.preventDefault();
    const created = await action.run(() => api("/tags", { method: "POST", body: { ...form, name: form.name.trim() } }));
    if (created) {
      setData([...tags, created].sort((a, b) => a.name.localeCompare(b.name)));
      setForm({ ...form, name: "" });
    }
  };

  return (
    <>
      <h1>Tags</h1>
      <p className="muted">Tags are shared by all users and can be attached to any task (many-to-many).</p>
      <section className="card">
        <form className="row" onSubmit={create}>
          <input placeholder="New tag name" required maxLength={50} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <input type="color" value={form.color} onChange={(e) => setForm({ ...form, color: e.target.value })} />
          <button className="btn" disabled={action.pending}>
            {action.pending ? "Adding..." : "Add tag"}
          </button>
        </form>
        <Alert>{action.error}</Alert>
      </section>
      {loading && <Spinner />}
      <Alert>{error}</Alert>
      {tags && (
        <ul className="tag-list card">
          {tags.map((tag) => (
            <TagRow
              key={tag.id}
              tag={tag}
              onSaved={(saved) => setData(tags.map((t) => (t.id === saved.id ? saved : t)))}
              onDeleted={(id) => setData(tags.filter((t) => t.id !== id))}
            />
          ))}
        </ul>
      )}
    </>
  );
}
