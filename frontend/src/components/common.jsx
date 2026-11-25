import { Navigate, NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../AuthContext";

export function Spinner({ label = "Loading..." }) {
  return (
    <div className="spinner" role="status">
      <span className="spinner-dot" /> {label}
    </div>
  );
}

export function Alert({ children, type = "error", onClose }) {
  if (!children) return null;
  return (
    <div className={`alert alert-${type}`} role={type === "error" ? "alert" : "status"}>
      <span>{children}</span>
      {onClose && (
        <button type="button" className="link" onClick={onClose} aria-label="Dismiss">
          ×
        </button>
      )}
    </div>
  );
}

export function TagChip({ tag }) {
  return (
    <span className="tag" style={{ background: tag.color }}>
      {tag.name}
    </span>
  );
}

// Routes only for logged-in users; others are sent to /login and returned back afterwards.
export function ProtectedRoute() {
  const { user, initializing } = useAuth();
  const location = useLocation();
  if (initializing) return <Spinner label="Checking session..." />;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  return <Outlet />;
}

// Login / signup pages are pointless when already logged in. This is also the
// single place that redirects after a successful login/signup.
export function GuestRoute() {
  const { user, initializing } = useAuth();
  const location = useLocation();
  if (initializing) return <Spinner label="Checking session..." />;
  if (user) {
    const target =
      location.state?.from?.pathname ?? (location.pathname === "/signup" ? "/profile" : "/my-projects");
    return <Navigate to={target} replace />;
  }
  return <Outlet />;
}

export function Layout() {
  const { user, logout, initializing } = useAuth();
  return (
    <>
      <header className="navbar">
        <NavLink to="/" className="brand">
          ✅ Task Tracker
        </NavLink>
        <nav>
          <NavLink to="/" end>
            Projects
          </NavLink>
          {user && <NavLink to="/my-projects">My projects</NavLink>}
          {user && <NavLink to="/tags">Tags</NavLink>}
        </nav>
        <div className="nav-right">
          {initializing ? null : user ? (
            <>
              <NavLink to="/profile">👤 {user.username}</NavLink>
              <button type="button" className="btn btn-outline" onClick={logout}>
                Log out
              </button>
            </>
          ) : (
            <>
              <NavLink to="/login">Log in</NavLink>
              <NavLink to="/signup" className="btn">
                Sign up
              </NavLink>
            </>
          )}
        </div>
      </header>
      <main className="container">
        <Outlet />
      </main>
    </>
  );
}
