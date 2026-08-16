import { Icon } from "./icons.jsx";

export default function StatCard({ icon = "clock", label, value, hint, tone = "session" }) {
  return (
    <article className={`card stat-card tone-${tone}`}>
      <div className="stat-icon">
        {typeof icon === "string" || icon == null ? <Icon name={icon || "clock"} /> : icon}
      </div>
      <div>
        <div className="label">{label}</div>
        <div className="value">{value ?? "—"}</div>
        {hint ? <div className="muted">{hint}</div> : null}
      </div>
    </article>
  );
}
