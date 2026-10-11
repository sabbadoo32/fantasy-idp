import { useEffect, useRef, useState } from "react";

// Fetch a JSON url and re-poll every `ms`. Returns { data, error, fetchedAt }.
// Cache-busts so the Netlify→Pages proxy always serves the freshest publish.
export function useData(url, ms) {
  const [state, setState] = useState({ data: null, error: null, fetchedAt: null });
  const timer = useRef(null);
  useEffect(() => {
    let alive = true;
    async function tick() {
      try {
        const r = await fetch(`${url}?t=${Date.now()}`, { cache: "no-store" });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = await r.json();
        if (alive) setState({ data, error: null, fetchedAt: Date.now() });
      } catch (e) {
        if (alive) setState((s) => ({ ...s, error: e.message }));
      }
    }
    tick();
    timer.current = setInterval(tick, ms);
    return () => { alive = false; clearInterval(timer.current); };
  }, [url, ms]);
  return state;
}
