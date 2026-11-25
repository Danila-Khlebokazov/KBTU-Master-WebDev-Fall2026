import { useCallback, useEffect, useRef, useState } from "react";

// Loads data with loading/error state. `loader` is called on mount and on reload().
export function useApi(loader, deps = []) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setData(await loaderRef.current());
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { data, setData, loading, error, reload };
}

// Wraps a mutation: tracks pending state and error.
// Returns the result (or true for empty 204 responses), undefined on error.
export function useAction() {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState(null);

  const run = useCallback(async (fn) => {
    setPending(true);
    setError(null);
    try {
      return (await fn()) ?? true;
    } catch (e) {
      setError(e.message);
      return undefined;
    } finally {
      setPending(false);
    }
  }, []);

  return { pending, error, setError, run };
}
