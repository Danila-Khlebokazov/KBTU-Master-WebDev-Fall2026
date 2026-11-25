import { useEffect, useState } from "react";
import { api, tokens } from "../api";
import { useAuth } from "../AuthContext";
import { Alert } from "../components/common";
import { useAction } from "../hooks";

const emptyToNull = (obj) =>
  Object.fromEntries(Object.entries(obj).map(([k, v]) => [k, v.trim() === "" ? null : v.trim()]));

function AccountInfo({ user }) {
  return (
    <section className="card">
      <h3>Current user</h3>
      <dl className="info">
        <dt>ID</dt>
        <dd>{user.id}</dd>
        <dt>Username</dt>
        <dd>{user.username}</dd>
        <dt>Name</dt>
        <dd>{user.name}</dd>
        <dt>Email</dt>
        <dd>{user.email}</dd>
        <dt>Member since</dt>
        <dd>{new Date(user.created_at).toLocaleDateString()}</dd>
        {user.profile?.job_title && (
          <>
            <dt>Job title</dt>
            <dd>{user.profile.job_title}</dd>
          </>
        )}
      </dl>
    </section>
  );
}

function AccountForm({ user, setUser }) {
  const [form, setForm] = useState({ username: user.username, name: user.name, email: user.email });
  const [success, setSuccess] = useState(null);
  const { pending, error, setError, run } = useAction();

  useEffect(() => setForm({ username: user.username, name: user.name, email: user.email }), [user]);

  const onSubmit = async (e) => {
    e.preventDefault();
    setSuccess(null);
    const changes = Object.fromEntries(Object.entries(form).filter(([k, v]) => v.trim() !== user[k]));
    if (Object.keys(changes).length === 0) {
      setError("Nothing changed");
      return;
    }
    const me = await run(() => api("/me", { method: "PATCH", body: changes }));
    if (me) {
      setUser(me);
      setSuccess("Account updated");
    }
  };

  return (
    <section className="card">
      <h3>Update username</h3>
      <Alert>{error}</Alert>
      <Alert type="success">{success}</Alert>
      <form className="form" onSubmit={onSubmit}>
        <label>
          Username
          <input
            required
            minLength={3}
            maxLength={50}
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
          />
        </label>
        <label>
          Full name
          <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </label>
        <label>
          Email
          <input type="email" required value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} />
        </label>
        <button className="btn" disabled={pending}>
          {pending ? "Saving..." : "Save changes"}
        </button>
      </form>
    </section>
  );
}

function PasswordForm() {
  const empty = { current_password: "", new_password: "", confirm: "" };
  const [form, setForm] = useState(empty);
  const [success, setSuccess] = useState(null);
  const { pending, error, setError, run } = useAction();
  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    setSuccess(null);
    if (form.new_password !== form.confirm) {
      setError("New passwords do not match");
      return;
    }
    const pair = await run(() =>
      api("/me/password", {
        method: "PUT",
        body: { current_password: form.current_password, new_password: form.new_password },
      }),
    );
    if (pair) {
      // Old tokens are revoked by the server; keep this session alive with the new pair
      tokens.set(pair);
      setForm(empty);
      setSuccess("Password changed. Other sessions were logged out.");
    }
  };

  return (
    <section className="card">
      <h3>Change password</h3>
      <Alert>{error}</Alert>
      <Alert type="success">{success}</Alert>
      <form className="form" onSubmit={onSubmit}>
        <label>
          Current password
          <input
            type="password"
            required
            autoComplete="current-password"
            value={form.current_password}
            onChange={set("current_password")}
          />
        </label>
        <label>
          New password
          <input
            type="password"
            required
            minLength={8}
            maxLength={72}
            autoComplete="new-password"
            value={form.new_password}
            onChange={set("new_password")}
          />
        </label>
        <label>
          Confirm new password
          <input type="password" required autoComplete="new-password" value={form.confirm} onChange={set("confirm")} />
        </label>
        <button className="btn" disabled={pending}>
          {pending ? "Changing..." : "Change password"}
        </button>
      </form>
    </section>
  );
}

function ProfileDetails({ user, setUser }) {
  const profile = user.profile;
  const toForm = (p) => ({
    bio: p?.bio ?? "",
    job_title: p?.job_title ?? "",
    location: p?.location ?? "",
    website: p?.website ?? "",
  });
  const [form, setForm] = useState(toForm(profile));
  const [success, setSuccess] = useState(null);
  const { pending, error, run } = useAction();
  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  useEffect(() => setForm(toForm(profile)), [profile]);

  const save = async (e) => {
    e.preventDefault();
    setSuccess(null);
    const saved = await run(() =>
      api("/me/profile", { method: profile ? "PUT" : "POST", body: emptyToNull(form) }),
    );
    if (saved) {
      setUser({ ...user, profile: saved });
      setSuccess(profile ? "Profile updated" : "Profile created");
    }
  };

  const remove = async () => {
    if (!window.confirm("Delete your profile details?")) return;
    setSuccess(null);
    if (await run(() => api("/me/profile", { method: "DELETE" }))) {
      setUser({ ...user, profile: null });
      setSuccess("Profile deleted");
    }
  };

  return (
    <section className="card">
      <h3>Profile details</h3>
      {!profile && <p className="muted small">You have no profile yet — fill in the form to create one.</p>}
      <Alert>{error}</Alert>
      <Alert type="success">{success}</Alert>
      <form className="form" onSubmit={save}>
        <label>
          Job title
          <input maxLength={100} value={form.job_title} onChange={set("job_title")} />
        </label>
        <label>
          Location
          <input maxLength={100} value={form.location} onChange={set("location")} />
        </label>
        <label>
          Website
          <input type="url" placeholder="https://..." maxLength={255} value={form.website} onChange={set("website")} />
        </label>
        <label>
          Bio
          <textarea rows={3} maxLength={5000} value={form.bio} onChange={set("bio")} />
        </label>
        <div className="row">
          <button className="btn" disabled={pending}>
            {pending ? "Saving..." : profile ? "Save profile" : "Create profile"}
          </button>
          {profile && (
            <button type="button" className="btn btn-danger" disabled={pending} onClick={remove}>
              Delete profile
            </button>
          )}
        </div>
      </form>
    </section>
  );
}

function DangerZone({ logout }) {
  const { pending, error, run } = useAction();
  const remove = async () => {
    if (!window.confirm("Delete your account? Your projects and their tasks will be deleted too.")) return;
    if (await run(() => api("/me", { method: "DELETE" }))) logout();
  };
  return (
    <section className="card danger">
      <h3>Danger zone</h3>
      <Alert>{error}</Alert>
      <button type="button" className="btn btn-danger" disabled={pending} onClick={remove}>
        {pending ? "Deleting..." : "Delete my account"}
      </button>
    </section>
  );
}

export default function Profile() {
  const { user, setUser, logout } = useAuth();
  return (
    <>
      <h1>Profile</h1>
      <div className="grid grid-2">
        <AccountInfo user={user} />
        <AccountForm user={user} setUser={setUser} />
        <PasswordForm />
        <ProfileDetails user={user} setUser={setUser} />
        <DangerZone logout={logout} />
      </div>
    </>
  );
}
