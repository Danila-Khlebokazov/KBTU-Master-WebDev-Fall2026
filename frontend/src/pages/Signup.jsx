import { useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../AuthContext";
import { Alert } from "../components/common";
import { useAction } from "../hooks";

export default function Signup() {
  const { signup } = useAuth();
  const [form, setForm] = useState({ username: "", name: "", email: "", password: "", confirm: "" });
  const { pending, error, setError, run } = useAction();
  const set = (field) => (e) => setForm({ ...form, [field]: e.target.value });

  const onSubmit = async (e) => {
    e.preventDefault();
    if (form.password !== form.confirm) {
      setError("Passwords do not match");
      return;
    }
    // On success <GuestRoute> redirects to /profile
    await run(() => signup(form));
  };

  return (
    <div className="auth-card card">
      <h2>Create an account</h2>
      <Alert>{error}</Alert>
      <form onSubmit={onSubmit} className="form">
        <label>
          Username
          <input
            required
            minLength={3}
            maxLength={50}
            pattern="[A-Za-z0-9._\-]+"
            title="Letters, digits, '.', '_' or '-'"
            autoComplete="username"
            value={form.username}
            onChange={set("username")}
          />
        </label>
        <label>
          Full name
          <input required maxLength={255} value={form.name} onChange={set("name")} />
        </label>
        <label>
          Email
          <input type="email" required autoComplete="email" value={form.email} onChange={set("email")} />
        </label>
        <label>
          Password <span className="muted small">(8–72 characters)</span>
          <input
            type="password"
            required
            minLength={8}
            maxLength={72}
            autoComplete="new-password"
            value={form.password}
            onChange={set("password")}
          />
        </label>
        <label>
          Confirm password
          <input type="password" required autoComplete="new-password" value={form.confirm} onChange={set("confirm")} />
        </label>
        <button className="btn" disabled={pending}>
          {pending ? "Creating account..." : "Sign up"}
        </button>
      </form>
      <p className="small muted">
        Already registered? <Link to="/login">Log in</Link>
      </p>
    </div>
  );
}
