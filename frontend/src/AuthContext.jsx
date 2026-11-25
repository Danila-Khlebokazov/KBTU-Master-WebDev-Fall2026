import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { api, tokens } from "./api";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [initializing, setInitializing] = useState(Boolean(tokens.access));
  const [notice, setNotice] = useState(null);

  // Restore the session from stored tokens on first load
  useEffect(() => {
    if (!tokens.access) return;
    api("/me")
      .then(setUser)
      .catch(() => tokens.clear())
      .finally(() => setInitializing(false));
  }, []);

  // Drop the user whenever tokens are cleared (logout or expired refresh token)
  useEffect(
    () =>
      tokens.onClear((reason) => {
        setUser(null);
        if (reason === "expired") setNotice("Your session has expired. Please log in again.");
      }),
    [],
  );

  const login = useCallback(async (username, password) => {
    const pair = await api("/auth/login", {
      method: "POST",
      body: { username, password },
      auth: false,
    });
    tokens.set(pair);
    const me = await api("/me");
    setNotice(null);
    setUser(me);
    return me;
  }, []);

  const signup = useCallback(
    async ({ username, email, name, password }) => {
      await api("/auth/signup", {
        method: "POST",
        body: { username, email, name, password },
        auth: false,
      });
      return login(username, password);
    },
    [login],
  );

  const logout = useCallback(() => tokens.clear("logout"), []);

  const value = useMemo(
    () => ({ user, setUser, initializing, login, signup, logout, notice, setNotice }),
    [user, initializing, login, signup, logout, notice],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
