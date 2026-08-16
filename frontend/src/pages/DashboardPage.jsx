import { useEffect, useState } from "react";
import ActivityTimeline from "../components/ActivityTimeline.jsx";
import AttendanceSummary from "../components/AttendanceSummary.jsx";
import DeviceStatus from "../components/DeviceStatus.jsx";
import EmptyState from "../components/EmptyState.jsx";
import LoadingState from "../components/LoadingState.jsx";
import StatCard from "../components/StatCard.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { getMyAttendanceOnDate, getMyLiveAttendance } from "../services/attendance.js";
import { useAuth } from "../hooks/useAuth.jsx";
import { apiError, displayName, formatDate, formatDuration, formatTime, greetingForHour, todayIso } from "../utils/format.js";
import { timelineFromAttendanceDay } from "../utils/timeline.js";

export default function DashboardPage() {
  const { user } = useAuth();
  const [live, setLive] = useState(null);
  const [day, setDay] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const date = live?.attendance_date || todayIso();

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const liveResponse = await getMyLiveAttendance();
        if (cancelled) return;
        setLive(liveResponse.data);
        const dayDate = liveResponse.data?.attendance_date || todayIso();
        try {
          const dayResponse = await getMyAttendanceOnDate(dayDate);
          if (!cancelled) setDay(dayResponse.data);
        } catch {
          if (!cancelled) setDay(null);
        }
      } catch (err) {
        if (!cancelled) setError(apiError(err, "Unable to load attendance"));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) return <LoadingState label="Loading your dashboard…" />;

  const status = live?.state || "OFFLINE";
  const connected = Boolean(live && live.state && live.state !== "OFFLINE");
  const timeline = timelineFromAttendanceDay(day);

  return (
    <div className="stack">
      <div className="greeting">
        <h1>
          {greetingForHour()}, {displayName(user)} 👋
        </h1>
        <p>Here&apos;s your work activity for today.</p>
        <p className="muted">{formatDate(date)}</p>
      </div>
      {error ? <div className="alert alert-error">{error}</div> : null}

      <section className="card hero-card">
        <div className="row-between">
          <div>
            <div className="muted">Current status</div>
            <div className="row" style={{ marginTop: "0.45rem" }}>
              <StatusBadge status={status} />
              <span className="muted">{connected ? "WorkPulse Agent Connected" : "WorkPulse Agent Disconnected"}</span>
            </div>
          </div>
          <div className="muted">As of {formatTime(live?.as_of)}</div>
        </div>
        <div style={{ marginTop: "1.2rem" }}>
          <div className="muted">Active time</div>
          <div className="metric">{formatDuration(day?.total_active_seconds)}</div>
        </div>
        <div className="grid grid-4" style={{ marginTop: "1.1rem" }}>
          <Mini label="Session time" value={formatDuration(day?.total_session_seconds)} />
          <Mini label="Idle time" value={formatDuration(day?.total_idle_seconds)} />
          <Mini label="Locked time" value={formatDuration(day?.total_locked_seconds)} />
          <Mini label="Device" value="—" />
        </div>
      </section>

      <section className="grid grid-4">
        <StatCard icon="activity" label="Active time" value={formatDuration(day?.total_active_seconds)} hint="Working time today" />
        <StatCard icon="clock" label="Session time" value={formatDuration(day?.total_session_seconds)} hint="Logged-in duration" />
        <StatCard icon="pause" label="Idle time" value={formatDuration(day?.total_idle_seconds)} hint="Inactivity windows" />
        <StatCard icon="lock" label="Locked time" value={formatDuration(day?.total_locked_seconds)} hint="Workstation locked" />
      </section>

      <section className="grid grid-2">
        <article className="card">
          <h2 className="card-title">Today&apos;s activity</h2>
          {timeline.length ? (
            <ActivityTimeline items={timeline} />
          ) : (
            <EmptyState title="No activity yet" message="Attendance sessions will appear here after the desktop agent records events." />
          )}
        </article>
        <div className="stack">
          <AttendanceSummary day={day} />
          <DeviceStatus
            connected={connected}
            deviceName={null}
            operatingSystem={null}
            lastSync={formatTime(live?.as_of)}
            pendingEvents={null}
          />
        </div>
      </section>
    </div>
  );
}

function Mini({ label, value }) {
  return (
    <div>
      <div className="muted">{label}</div>
      <strong>{value}</strong>
    </div>
  );
}
