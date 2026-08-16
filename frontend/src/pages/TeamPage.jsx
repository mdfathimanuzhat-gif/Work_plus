import { useEffect, useMemo, useState } from "react";
import Avatar from "../components/Avatar.jsx";
import EmptyState from "../components/EmptyState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import StatCard from "../components/StatCard.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { useAuth } from "../hooks/useAuth.jsx";
import { getTeamAttendance } from "../services/attendance.js";
import { listEmployees, listTeamMembers } from "../services/people.js";
import { apiError, displayName, formatDuration, todayIso } from "../utils/format.js";

export default function TeamPage() {
  const { user, hasRole } = useAuth();
  const [members, setMembers] = useState([]);
  const [records, setRecords] = useState([]);
  const [date, setDate] = useState(todayIso());
  const [error, setError] = useState("");

  useEffect(() => {
    const loader = user?.team_id ? listTeamMembers(user.team_id) : hasRole("HR", "ADMIN") ? listEmployees() : null;
    if (!loader) {
      setError("You are not assigned to a team.");
      return;
    }
    loader
      .then((response) => setMembers(response.data))
      .catch((err) => setError(apiError(err, "Unable to load team")));
  }, [user, hasRole]);

  useEffect(() => {
    getTeamAttendance(date)
      .then((response) => setRecords(response.data?.records || []))
      .catch(() => setRecords([]));
  }, [date]);

  const byEmployee = useMemo(() => Object.fromEntries(records.map((row) => [row.employee_id, row])), [records]);
  const present = records.filter((row) => row.status === "PRESENT" || row.session_count > 0).length;
  const incomplete = records.filter((row) => row.status === "INCOMPLETE" || row.status === "PARTIAL").length;
  const absent = members.length ? Math.max(0, members.length - present) : records.filter((row) => row.status === "ABSENT").length;

  return (
    <div className="stack">
      <PageHeader
        title="Team"
        subtitle="Team attendance for the selected day."
        actions={<input className="input" type="date" value={date} onChange={(event) => setDate(event.target.value)} />}
      />
      <section className="grid grid-4">
        <StatCard icon="users" label="People" value={members.length || records.length || "—"} hint="Visible employees" />
        <StatCard icon="activity" label="With sessions" value={present || "—"} hint="Present / activity recorded" />
        <StatCard icon="pause" label="Incomplete" value={incomplete || "—"} hint="Partial days" />
        <StatCard icon="calendar" label="No activity" value={absent || "—"} hint="No session on this date" />
      </section>
      {error ? <div className="alert alert-error">{error}</div> : null}
      <article className="card">
        {!members.length ? <EmptyState title="No team members" message="There are no people to display." /> : null}
        {members.length ? (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>Status</th>
                  <th>Attendance</th>
                  <th>Active</th>
                  <th>Idle</th>
                  <th>Locked</th>
                </tr>
              </thead>
              <tbody>
                {members.map((member) => {
                  const attendance = byEmployee[member.id];
                  return (
                    <tr key={member.id}>
                      <td>
                        <div className="person">
                          <Avatar first={member.first_name} last={member.last_name} />
                          <div>
                            <strong>{displayName(member)}</strong>
                            <div className="muted">{member.employee_code}</div>
                          </div>
                        </div>
                      </td>
                      <td>
                        <StatusBadge status={member.employment_status} />
                      </td>
                      <td>{attendance ? <StatusBadge status={attendance.status} /> : "—"}</td>
                      <td>{formatDuration(attendance?.total_active_seconds)}</td>
                      <td>{formatDuration(attendance?.total_idle_seconds)}</td>
                      <td>{formatDuration(attendance?.total_locked_seconds)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : null}
      </article>
    </div>
  );
}
