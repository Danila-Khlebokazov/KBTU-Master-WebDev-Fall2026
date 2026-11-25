import { Link } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../AuthContext";
import { Alert, Spinner } from "../components/common";
import { useApi } from "../hooks";

// Public page: uses only public GET endpoints.
export default function Home() {
  const { user } = useAuth();
  const { data, loading, error, reload } = useApi(async () => {
    const [projects, users] = await Promise.all([
      api("/projects?limit=100", { auth: false }),
      api("/users?limit=100", { auth: false }),
    ]);
    return { projects, users: Object.fromEntries(users.map((u) => [u.id, u])) };
  });

  return (
    <>
      <section className="hero">
        <h1>All projects</h1>
        <p className="muted">
          Anyone can browse projects. {user ? "Open a project to see its board." : "Log in to manage your own projects and tasks."}
        </p>
      </section>

      {loading && <Spinner />}
      {error && (
        <Alert>
          {error}{" "}
          <button type="button" className="link" onClick={reload}>
            Retry
          </button>
        </Alert>
      )}

      {data && (
        <div className="grid">
          {data.projects.length === 0 && <p className="muted">No projects yet.</p>}
          {data.projects.map((p) => (
            <article key={p.id} className="card">
              <h3>{p.name}</h3>
              <p className="muted">{p.description || "No description"}</p>
              <p className="small">
                Owner: <b>{data.users[p.owner_id]?.name ?? `#${p.owner_id}`}</b>
                {user?.id === p.owner_id && <span className="badge">you</span>}
              </p>
              {user ? (
                <Link to={`/projects/${p.id}`} className="btn btn-outline btn-sm">
                  Open board →
                </Link>
              ) : (
                <Link to="/login" className="small">
                  Log in to open the board
                </Link>
              )}
            </article>
          ))}
        </div>
      )}
    </>
  );
}
