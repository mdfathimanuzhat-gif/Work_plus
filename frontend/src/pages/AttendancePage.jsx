import { useCallback, useEffect, useMemo, useState } from "react";

import ActivityTimeline from "../components/ActivityTimeline.jsx";
import DataTable from "../components/DataTable.jsx";
import EmptyState from "../components/EmptyState.jsx";
import { Icon } from "../components/icons.jsx";
import LoadingState from "../components/LoadingState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import StatCard from "../components/StatCard.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { useLiveSeconds } from "../hooks/useLiveSeconds.js";
import { getMyAttendance, getMyAttendanceDay, getMyAttendanceLive } from "../services/attendance.js";
import { formatDate, formatDuration, formatTime, todayIso, userMessage } from "../utils/format.js";
import { timelineFromAttendanceDay } from "../utils/timeline.js";

export default function AttendancePage() {
  const today = todayIso();
  const [date, setDate] = useState(today);
  const [live, setLive] = useState(null);
  const [day, setDay] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const [livePayload, dayPayload, list] = await Promise.all([
        getMyAttendanceLive(),
        getMyAttendanceDay(date),
        getMyAttendance(),
      ]);
      setLive(livePayload);
      setDay(dayPayload);
      setHistory(Array.isArray(list.data) ? list.data : []);
    } catch (err) {
      setError(userMessage(err, "We couldn't load attendance."));
    } finally {
      setLoading(false);
    }
  }, [date]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  const ticking = date === today && live?.state === "ACTIVE";
  const displaySeconds = useLiveSeconds(day?.total_active_seconds, live?.as_of, ticking);
  const timeline = useMemo(() => timelineFromAttendanceDay(day), [day]);
  const activeValue = date === today ? displaySeconds : day?.total_active_seconds;

  return (
    <div className="stack">
      <PageHeader
        title="My Attendance"
        subtitle="Sessions, durations, and daily history"
        actions={
          <label className="label" style={{ margin: 0, minWidth: 180 }}>
            Date
            <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </label>
        }
      />

      {error ? <div className="alert alert-error">{error}</div> : null}
      {loading ? (
        <LoadingState kind="stats" />
      ) : (
        <section className="grid grid-4">
          <StatCard tone="active" label="Active Time" value={formatDuration(activeValue)} hint="Working time" icon="clock" />
          <StatCard tone="idle" label="Idle Time" value={formatDuration(day?.total_idle_seconds)} hint="Idle intervals" icon="pause" />
          <StatCard tone="locked" label="Locked Time" value={formatDuration(day?.total_locked_seconds)} hint="Lock intervals" icon="lock" />
          <StatCard tone="session" label="Sessions" value={day?.session_count ?? "—"} hint="Recorded sessions" icon="session" />
        </section>
      )}

      <article className="card">
        <h2 className="card-title">Attendance timeline</h2>
        {loading ? (
          <LoadingState kind="timeline" />
        ) : timeline.length ? (
          <ActivityTimeline items={timeline} />
        ) : (
          <EmptyState icon={<Icon name="calendar" />} title="No activity recorded yet." body="Nothing is on file for this date." />
        )}
      </article>

      <article className="card">
        <h2 className="card-title">Daily attendance history</h2>
        <DataTable
          columns={[
            { key: "date", header: "Date", render: (row) => formatDate(row.attendance_date) },
            { key: "login", header: "First Login", render: (row) => formatTime(row.first_login_time) },
            { key: "logout", header: "Last Logout", render: (row) => formatTime(row.last_logout_time) },
            { key: "active", header: "Active", render: (row) => formatDuration(row.total_active_seconds) },
            { key: "idle", header: "Idle", render: (row) => formatDuration(row.total_idle_seconds) },
            { key: "locked", header: "Locked", render: (row) => formatDuration(row.total_locked_seconds) },
            {
              key: "status",
              header: "Status",
              render: (row) => <StatusBadge status={row.attendance_date === today ? live?.state || row.status : row.status} />,
            },
          ]}
          rows={history}
          emptyTitle="No attendance history yet."
        />
      </article>
    </div>
  );
}
