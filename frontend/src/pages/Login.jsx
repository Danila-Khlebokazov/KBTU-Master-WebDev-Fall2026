import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../AuthContext";
import { Alert } from "../components/common";
import { useAction } from "../hooks";

export default function Login() {
  const { login, notice, setNotice } = useAuth();
  const [form, setForm] = useState({ username: "", password: "" });
  const { pending, error, run } = useAction();

  const onSubmit = async (e) => {
    e.preventDefault();
    // On success <GuestRoute> redirects back to the page the user came from
    await run(() => login(form.username, form.password));
  };

  return (
    <div className="auth-card card">
      <h2>Log in</h2>
      <Alert type="info" onClose={() => setNotice(null)}>
        {notice}
      </Alert>
      <Alert>{error}</Alert>
      <form onSubmit={onSubmit} className="form">
        <label>
          Username
          <input
            autoComplete="username"
            required
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
          />
        </label>
        <label>
          Password
          <input
            type="password"
            autoComplete="current-password"
            required
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
        </label>
        <button className="btn" disabled={pending}>
          {pending ? "Logging in..." : "Log in"}
        </button>
      </form>
      <p className="small muted">
        No account? <Link to="/signup">Sign up</Link>. Demo user: <code>alina.kim</code> /{" "}
        <code>password123</code>
      </p>
    </div>
  );
}
