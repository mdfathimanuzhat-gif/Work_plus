export default function LoadingState({ label = "Loading…", kind = "dashboard" }) {
  if (kind === "table") {
    return (
      <div className="card">
        <div className="skeleton sk-line" style={{ width: "30%" }} />
        <div className="skeleton sk-line" />
        <div className="skeleton sk-line" />
        <div className="skeleton sk-line" style={{ width: "70%" }} />
        <span className="sr-only">{label}</span>
      </div>
    );
  }
  if (kind === "timeline" || kind === "card") {
    return (
      <div className="stack">
        <div className="skeleton sk-card" style={{ height: kind === "card" ? 160 : 220 }} />
        <span className="sr-only">{label}</span>
      </div>
    );
  }
  if (kind === "stats") {
    return (
      <div className="grid grid-4">
        <div className="skeleton sk-card" />
        <div className="skeleton sk-card" />
        <div className="skeleton sk-card" />
        <div className="skeleton sk-card" />
        <span className="sr-only">{label}</span>
      </div>
    );
  }
  return (
    <div className="stack">
      <div className="skeleton sk-line" style={{ width: "40%" }} />
      <div className="grid grid-4">
        <div className="skeleton sk-card" />
        <div className="skeleton sk-card" />
        <div className="skeleton sk-card" />
        <div className="skeleton sk-card" />
      </div>
      <div className="skeleton sk-card" style={{ height: 180 }} />
      <span className="sr-only">{label}</span>
    </div>
  );
}
