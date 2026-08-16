import { useEffect, useState } from "react";

export function useLiveSeconds(baseSeconds, asOf, ticking) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!ticking) return undefined;
    const id = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(id);
  }, [ticking]);
  const extra = ticking && asOf ? Math.max(0, (now - new Date(asOf).getTime()) / 1000) : 0;
  const base = Number.isFinite(Number(baseSeconds)) ? Number(baseSeconds) : 0;
  return Math.floor(base + extra);
}
