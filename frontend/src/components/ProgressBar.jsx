export default function ProgressBar({ value = 0, tone = "active" }) {
  const width = Math.max(0, Math.min(100, Number(value) || 0));
  return (
    <div className={`bar bar-${tone}`}>
      <span style={{ width: `${width}%` }} />
    </div>
  );
}

export function ProgressRing({ value = 0, label, sublabel, primary }) {
  const pct = Math.max(0, Math.min(100, Number(value) || 0));
  const r = 42;
  const c = 2 * Math.PI * r;
  const offset = c - (pct / 100) * c;
  return (
    <div className="row" style={{ gap: "1rem" }}>
      <svg className="ring" width="108" height="108" viewBox="0 0 108 108">
        <circle className="ring-bg" cx="54" cy="54" r={r} />
        <circle className="ring-fg" cx="54" cy="54" r={r} strokeDasharray={c} strokeDashoffset={offset} />
      </svg>
      <div>
        <div className="muted">{label}</div>
        <div className="value" style={{ fontSize: "1.6rem", fontWeight: 730 }}>
          {primary ?? `${Math.round(pct)}%`}
        </div>
        <div className="muted">{sublabel}</div>
      </div>
    </div>
  );
}
