import { formatDuration, formatTime } from "../utils/format.js";

export default function AttendanceSummary({ day }) {
  const active = day?.total_active_seconds ?? 0;
  const session = day?.total_session_seconds ?? 0;
  const ratio = session > 0 ? Math.min(100, Math.round((active / session) * 100)) : 0;
  return (
    <article className="card">
      <h2 className="card-title">Attendance summary</h2>
      <dl className="details">
        <dt>First login</dt>
        <dd>{formatTime(day?.first_login_time)}</dd>
        <dt>Last logout</dt>
        <dd>{formatTime(day?.last_logout_time)}</dd>
        <dt>Active time</dt>
        <dd>{formatDuration(day?.total_active_seconds)}</dd>
        <dt>Idle time</dt>
        <dd>{formatDuration(day?.total_idle_seconds)}</dd>
        <dt>Locked time</dt>
        <dd>{formatDuration(day?.total_locked_seconds)}</dd>
        <dt>Sessions</dt>
        <dd>{day?.session_count ?? "—"}</dd>
      </dl>
      <div style={{ marginTop: "1rem" }}>
        <div className="row-between">
          <span className="muted">Active share of session time</span>
          <span className="muted">{day ? `${ratio}%` : "—"}</span>
        </div>
        <div className="progress" style={{ marginTop: "0.4rem" }}>
          <span style={{ width: `${day ? ratio : 0}%` }} />
        </div>
      </div>
    </article>
  );
}
