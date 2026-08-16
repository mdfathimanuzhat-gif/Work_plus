import { Icon } from "./icons.jsx";

export default function StatCard({ icon, label, value, hint }) {
  return (
    <article className="card stat-card">
      <div className="stat-icon">
        <Icon name={icon} />
      </div>
      <div>
        <div className="label">{label}</div>
        <div className="value">{value ?? "—"}</div>
        {hint ? <div className="muted">{hint}</div> : null}
      </div>
    </article>
  );
}
