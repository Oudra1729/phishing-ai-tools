import { useCallback, useEffect, useState } from "react";

const KEY = "phishing_analyzer_history_v1";
const MAX = 5;

export function useHistory() {
  const [items, setItems] = useState([]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem(KEY);
      if (raw) setItems(JSON.parse(raw));
    } catch {
      setItems([]);
    }
  }, []);

  const push = useCallback((entry) => {
    setItems((prev) => {
      const next = [
        { ...entry, at: new Date().toISOString() },
        ...prev.filter((x) => x.url !== entry.url),
      ].slice(0, MAX);
      try {
        localStorage.setItem(KEY, JSON.stringify(next));
      } catch {
        /* ignore */
      }
      return next;
    });
  }, []);

  const clear = useCallback(() => {
    setItems([]);
    try {
      localStorage.removeItem(KEY);
    } catch {
      /* ignore */
    }
  }, []);

  return { items, push, clear };
}
