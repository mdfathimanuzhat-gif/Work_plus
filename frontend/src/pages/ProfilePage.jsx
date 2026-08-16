import { useEffect, useState } from "react";

import Avatar from "../components/Avatar.jsx";
import LoadingState from "../components/LoadingState.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { useAuth } from "../hooks/useAuth.jsx";
import { getMyProfile } from "../services/people.js";
import { display, displayName, primaryRole, userMessage } from "../utils/format.js";

export default function ProfilePage() {
  const { user } = useAuth();
  const [profile, setProfile] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getMyProfile()
      .then((response) => setProfile(response.data))
      .catch((err) => setError(userMessage(err, "We couldn't load your profile.")));
  }, []);

  if (!user) {
    return (
      <div className="stack">
        <div className="alert alert-error">You need to sign in to view this page.</div>
      </div>
    );
  }

  const person = profile || user;

  return (
    <div className="stack">
      {error ? <div className="alert alert-error">{error}</div> : null}
      {!profile && !error ? <LoadingState kind="card" /> : null}
      <article className="card">
        <div className="person" style={{ gap: "1rem" }}>
          <Avatar first={person.first_name} last={person.last_name} size="lg" />
          <div>
            <h1 style={{ margin: 0, letterSpacing: "-0.03em" }}>{displayName(person)}</h1>
            <p className="muted">{person.email}</p>
            <div className="row" style={{ marginTop: 10 }}>
              <StatusBadge status={person.is_active === false ? "OFFLINE" : "ACTIVE"} />
              <span className="badge badge-muted">{primaryRole(person.roles || user.roles)}</span>
            </div>
          </div>
        </div>
      </article>

      <section className="grid grid-3">
        <InfoCard label="Employee ID" value={display(person.employee_code)} />
        <InfoCard label="Role" value={primaryRole(person.roles || user.roles)} />
        <InfoCard label="Department" value={display(person.department_name)} />
        <InfoCard label="Team" value={display(person.team_name)} />
        <InfoCard label="Account status" value={display(person.account_status || (person.is_active === false ? "Inactive" : "Active"))} />
        <InfoCard label="Employment" value={display(person.employment_status)} />
      </section>
    </div>
  );
}

function InfoCard({ label, value }) {
  return (
    <article className="card">
      <p className="muted" style={{ margin: 0 }}>{label}</p>
      <p style={{ fontSize: 18, fontWeight: 700, margin: "8px 0 0", letterSpacing: "-0.03em" }}>{value}</p>
    </article>
  );
}
