import { useAuth } from "../hooks/useAuth.jsx";
import PageHeader from "../components/PageHeader.jsx";
import { displayName, primaryRole } from "../utils/format.js";

export default function SettingsPage() {
  const { user } = useAuth();
  return (
    <div className="stack">
      <PageHeader title="Settings" subtitle="Account preferences for this workstation." />
      <article className="card">
        <h2 className="card-title">Session</h2>
        <dl className="details">
          <dt>Signed in as</dt>
          <dd>{displayName(user)}</dd>
          <dt>Email</dt>
          <dd>{user?.email || "—"}</dd>
          <dt>Role</dt>
          <dd>{primaryRole(user?.roles)}</dd>
        </dl>
        <p className="muted" style={{ marginTop: "1rem" }}>
          Notification delivery is not configured in this phase.
        </p>
      </article>
    </div>
  );
}
