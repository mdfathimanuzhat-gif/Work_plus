import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import ActivityTimeline from "../components/ActivityTimeline.jsx";
import DeviceStatusCard from "../components/DeviceStatusCard.jsx";
import EmptyState from "../components/EmptyState.jsx";
import { Icon } from "../components/icons.jsx";
import LiveStatusCard from "../components/LiveStatusCard.jsx";
import LoadingState from "../components/LoadingState.jsx";
import { ProgressRing } from "../components/ProgressBar.jsx";
import ProgressBar from "../components/ProgressBar.jsx";
import StatCard from "../components/StatCard.jsx";
import { useAuth } from "../hooks/useAuth.jsx";
import { useLiveSeconds } from "../hooks/useLiveSeconds.js";
import { getMyAttendanceDay, getMyAttendanceLive } from "../services/attendance.js";
import { firstName, formatClock, formatDuration, todayIso, userMessage } from "../utils/format.js";
import { timelineFromAttendanceDay } from "../utils/timeline.js";

const TARGET_SECONDS = 8 * 3600;

function greeting(date) {
  const hour = date.getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

function barWidth(value, day) {
  const total =
    (Number(day?.total_active_seconds) || 0) +
    (Number(day?.total_idle_seconds) || 0) +
    (Number(day?.total_locked_seconds) || 0);
  if (!total || value == null) return 0;
  return Math.min(100, (Number(value) / total) * 100);
}

export default function DashboardPage() {
  const { user } = useAuth();
  const today = todayIso();
  const [live, setLive] = useState(null);
  const [day, setDay] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      const [livePayload, dayPayload] = await Promise.all([
        getMyAttendanceLive(),
        getMyAttendanceDay(today),
      ]);
      setLive(livePayload);
      setDay(dayPayload);
    } catch (err) {
      setError(userMessage(err, "We couldn't load today's activity."));
    } finally {
      setLoading(false);
    }
  }, [today]);

  useEffect(() => {
    load();
    const id = window.setInterval(load, 15000);
    return () => window.clearInterval(id);
  }, [load]);

  const ticking = live?.state === "ACTIVE";
  const displaySeconds = useLiveSeconds(day?.total_active_seconds, live?.as_of, ticking);
  const timeline = useMemo(() => timelineFromAttendanceDay(day), [day]);
  const progress = TARGET_SECONDS > 0 ? Math.min(100, (displaySeconds / TARGET_SECONDS) * 100) : 0;

  if (loading && !live && !day) {
    return (
      <div className="stack">
        <LoadingState kind="dashboard" />
      </div>
    );
  }

  return (
    <div className="stack">
      <header className="greeting-row">
        <div className="greeting">
          <h1>
            {greeting(new Date())}, {firstName(user)}{" "}
            <span aria-hidden="true">👋</span>
          </h1>
          <p>Here's your work activity for today.</p>
          <p className="muted" style={{ marginTop: 6 }}>{formatClock(new Date())}</p>
        </div>
        <span className="live-chip">
          <span className="pulse" />
          LIVE
        </span>
      </header>

      {error ? (
        <div className="alert alert-error">
          {error}{" "}
          <button type="button" className="btn btn-ghost" onClick={load}>
            Retry
          </button>
        </div>
      ) : null}

      <LiveStatusCard live={live} day={day} />

      <section className="grid grid-4">
        <StatCard
          tone="active"
          label="Active Time"
          value={formatDuration(displaySeconds)}
          hint="Counted as working time"
          icon="clock"
        />
        <StatCard
          tone="session"
          label="Session Time"
          value={day?.session_count ?? "—"}
          hint="Sessions recorded today"
          icon="session"
        />
        <StatCard
          tone="idle"
          label="Idle Time"
          value={formatDuration(day?.total_idle_seconds)}
          hint="Away from keyboard"
          icon="pause"
        />
        <StatCard
          tone="locked"
          label="Locked Time"
          value={formatDuration(day?.total_locked_seconds)}
          hint="Workstation locked"
          icon="lock"
        />
      </section>

      <section className="grid grid-2">
        <article className="card">
          <div className="row-between">
            <div>
              <h2 className="card-title" style={{ marginBottom: 4 }}>Today's Activity</h2>
              <p className="muted">Sessions and attendance notes from today</p>
            </div>
            <Link to="/history" className="btn btn-ghost">
              View all
            </Link>
          </div>
          {timeline.length ? (
            <ActivityTimeline items={timeline} />
          ) : (
            <EmptyState
              icon={<Icon name="activity" />}
              title="No activity recorded yet."
              body="Events from the WorkPulse Agent will appear here after they are processed."
            />
          )}
        </article>

        <article className="card">
          <h2 className="card-title">Attendance Overview</h2>
          <p className="muted">Today's Active Time</p>
          <ProgressRing
            value={progress}
            label="Today's Active Time"
            primary={formatDuration(displaySeconds)}
            sublabel="Target: 08h 00m"
          />
          <div className="stack" style={{ marginTop: 16, gap: 10 }}>
            <div>
              <div className="row-between">
                <span>Active</span>
                <strong>{formatDuration(displaySeconds)}</strong>
              </div>
              <ProgressBar value={barWidth(day?.total_active_seconds, day)} tone="active" />
            </div>
            <div>
              <div className="row-between">
                <span>Idle</span>
                <strong>{formatDuration(day?.total_idle_seconds)}</strong>
              </div>
              <ProgressBar value={barWidth(day?.total_idle_seconds, day)} tone="idle" />
            </div>
            <div>
              <div className="row-between">
                <span>Locked</span>
                <strong>{formatDuration(day?.total_locked_seconds)}</strong>
              </div>
              <ProgressBar value={barWidth(day?.total_locked_seconds, day)} tone="locked" />
            </div>
          </div>
        </article>
      </section>

      <DeviceStatusCard live={live} />
    </div>
  );
}
