import { useEffect, useState } from "react";
import ActivityTimeline from "../components/ActivityTimeline.jsx";
import AttendanceSummary from "../components/AttendanceSummary.jsx";
import EmptyState from "../components/EmptyState.jsx";
import LoadingState from "../components/LoadingState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import StatCard from "../components/StatCard.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { getMyAttendanceOnDate, getMyLiveAttendance } from "../services/attendance.js";
import { apiError, formatDuration, formatTime, todayIso } from "../utils/format.js";
import { timelineFromAttendanceDay } from "../utils/timeline.js";

export default function AttendancePage() {
  const [date, setDate] = useState(todayIso());
  const [live, setLive] = useState(null);
  const [day, setDay] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getMyLiveAttendance()
      .then((response) => setLive(response.data))
      .catch(() => setLive(null));
  }, []);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError("");
    getMyAttendanceOnDate(date)
      .then((response) => {
        if (!cancelled) setDay(response.data);
      })
      .catch((err) => {
        if (!cancelled) {
          setDay(null);
          setError(apiError(err, "No attendance record for this date"));
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [date]);

  const timeline = timelineFromAttendanceDay(day);

  return (
    <div className="stack">
      <PageHeader
        title="Attendance"
        subtitle="Daily sessions and working-hour breakdown."
        actions={<input className="input" type="date" value={date} onChange={(event) => setDate(event.target.value)} />}
      />
      <div className="row" style={{ gap: "1rem" }}>
        <span className="muted">Current status</span>
        <StatusBadge status={live?.state || "OFFLINE"} />
      </div>
      {error ? <div className="alert alert-error">{error}</div> : null}
      {loading ? <LoadingState /> : null}
      <section className="grid grid-4">
        <StatCard icon="activity" label="Active" value={formatDuration(day?.total_active_seconds)} />
        <StatCard icon="clock" label="Session" value={formatDuration(day?.total_session_seconds)} />
        <StatCard icon="pause" label="Idle" value={formatDuration(day?.total_idle_seconds)} />
        <StatCard icon="lock" label="Locked" value={formatDuration(day?.total_locked_seconds)} />
      </section>
      <section className="grid grid-2">
        <article className="card">
          <h2 className="card-title">Daily timeline</h2>
          {timeline.length ? <ActivityTimeline items={timeline} /> : <EmptyState title="No sessions" message="There is no session timeline for this date." />}
        </article>
        <AttendanceSummary day={day} />
      </section>
      <article className="card">
        <h2 className="card-title">Sessions</h2>
        {day?.sessions?.length ? (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Start</th>
                  <th>End</th>
                  <th>Active</th>
                  <th>Idle</th>
                  <th>Locked</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {day.sessions.map((session) => (
                  <tr key={session.id}>
                    <td>{formatTime(session.session_start)}</td>
                    <td>{formatTime(session.session_end)}</td>
                    <td>{formatDuration(session.active_seconds)}</td>
                    <td>{formatDuration(session.idle_seconds)}</td>
                    <td>{formatDuration(session.locked_seconds)}</td>
                    <td>
                      <StatusBadge status={session.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="No session rows" message="Sessions appear after the attendance engine processes events." />
        )}
      </article>
    </div>
  );
}
