import { useEffect, useState } from "react";
import Avatar from "../components/Avatar.jsx";
import LoadingState from "../components/LoadingState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { useAuth } from "../hooks/useAuth.jsx";
import { getMyProfile, updateEmployee } from "../services/people.js";
import { apiError, displayName } from "../utils/format.js";

export default function ProfilePage() {
  const { user } = useAuth();
  const [profile, setProfile] = useState(null);
  const [phone, setPhone] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getMyProfile()
      .then((response) => {
        setProfile(response.data);
        setPhone(response.data.phone || "");
      })
      .catch((err) => setError(apiError(err, "Unable to load profile")));
  }, []);

  async function handleSave(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setSaving(true);
    try {
      const response = await updateEmployee(user.employee_id, { phone });
      setProfile(response.data);
      setMessage("Profile updated");
    } catch (err) {
      setError(apiError(err, "Unable to update profile"));
    } finally {
      setSaving(false);
    }
  }

  if (!profile) return <LoadingState />;

  return (
    <div className="stack">
      <PageHeader title="Profile" subtitle="Your employee record and contact details." />
      <article className="card">
        <div className="person" style={{ gap: "1rem" }}>
          <Avatar first={profile.first_name} last={profile.last_name} size="lg" />
          <div>
            <h2 style={{ margin: 0 }}>{displayName(profile)}</h2>
            <p className="muted" style={{ margin: "0.2rem 0 0" }}>
              {profile.employee_code} · {profile.email}
            </p>
            <div className="row" style={{ marginTop: "0.5rem" }}>
              <StatusBadge status={profile.employment_status} />
              <span className="badge badge-muted">{profile.account_status}</span>
            </div>
          </div>
        </div>
      </article>
      <div className="grid grid-2">
        <article className="card">
          <h2 className="card-title">Employee information</h2>
          <dl className="details">
            <dt>Department</dt>
            <dd>{profile.department_name || "—"}</dd>
            <dt>Team</dt>
            <dd>{profile.team_name || "—"}</dd>
            <dt>Reporting team lead</dt>
            <dd>{profile.manager_name || "—"}</dd>
            <dt>Joining date</dt>
            <dd>{profile.joining_date || "—"}</dd>
            <dt>Roles</dt>
            <dd>{profile.roles?.join(", ") || "—"}</dd>
          </dl>
        </article>
        <article className="card">
          <h2 className="card-title">Personal details</h2>
          <form className="stack" onSubmit={handleSave}>
            <label className="label">
              Phone
              <input className="input" value={phone} onChange={(event) => setPhone(event.target.value)} />
            </label>
            {message ? <div className="alert alert-success">{message}</div> : null}
            {error ? <div className="alert alert-error">{error}</div> : null}
            <button className="btn" type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </button>
          </form>
        </article>
      </div>
    </div>
  );
}
