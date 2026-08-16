import { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import ActivityTimeline from "../components/ActivityTimeline.jsx";
import DeviceStatusCard from "../components/DeviceStatusCard.jsx";
import EmptyState from "../components/EmptyState.jsx";
import { Icon } from "../components/icons.jsx";
import LoadingState from "../components/LoadingState.jsx";
import StatCard from "../components/StatCard.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { useAuth } from "../hooks/useAuth.jsx";
import { useLiveSeconds } from "../hooks/useLiveSeconds.js";
import { getMyAttendanceDay, getMyAttendanceLive } from "../services/attendance.js";
import {
  displayName,
  firstName,
  formatClock,
  formatDuration,
  formatTime,
  primaryRole,
  splitDuration,
  statusCopy,
  todayIso,
  userMessage,
} from "../utils/format.js";
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

  const status = live?.state || "OFFLINE";
  const connected = Boolean(live && status !== "OFFLINE");
  const timer = splitDuration(displaySeconds);
  const deviceName = live?.device_name || live?.hostname || day?.device_name || "—";

  if (loading && !live && !day) {
    return (
      <div className="stack">
        <LoadingState kind="dashboard" />
      </div>
    );
  }

  return (
    <div className="dash">
      <header className="dash-header">
        <div>
          <p className="dash-kicker">{formatClock(new Date())}</p>
          <h1>
            {greeting(new Date())}, {firstName(user)}
          </h1>
          <p className="dash-sub">Here's your work activity for today.</p>
        </div>
        <div className="dash-header-meta">
          <div className="dash-user-card">
            <span className="dash-user-name">{displayName(user)}</span>
            <span className="dash-user-role">{primaryRole(user?.roles)}</span>
          </div>
          <span className="live-chip">
            <span className="pulse" />
            LIVE
          </span>
        </div>
      </header>

      {error ? (
        <div className="alert alert-error">
          {error}{" "}
          <button type="button" className="btn btn-ghost" onClick={load}>
            Retry
          </button>
        </div>
      ) : null}

      <section className={`card dash-hero dash-hero-${status.toLowerCase()}`}>
        <div className="dash-hero-copy">
          <p className="dash-kicker">Current status</p>
          <div className="dash-hero-status">
            <StatusBadge status={status} />
            <h2>{status}</h2>
          </div>
          <p className="dash-sub">{statusCopy(status)}</p>
          <div className={`dash-agent ${connected ? "is-on" : "is-off"}`}>
            <span className="pulse" />
            {connected ? "WorkPulse Agent Connected" : "WorkPulse Agent Disconnected"}
          </div>
          <p className="muted dash-device-line">Device: {deviceName}</p>
        </div>
        <div className="dash-hero-timer">
          <div className="clock-hms">
            <div className="hm">
              {timer.hours}h {timer.minutes}m
            </div>
            <div className="sec">{timer.seconds}s</div>
          </div>
          <p className="muted">Active today</p>
          <div className="dash-target">
            <div className="row-between">
              <span className="muted">Toward 08h 00m</span>
              <span className="muted">{Math.round(progress)}%</span>
            </div>
            <div className="progress">
              <span style={{ width: `${progress}%` }} />
            </div>
          </div>
        </div>
      </section>

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
          value={formatDuration(day?.total_session_seconds)}
          hint="Total time in session"
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
        <article className="card dash-summary">
          <h2 className="card-title">Attendance summary</h2>
          <div className="summary-tiles">
            <div className="summary-tile">
              <span>First Login</span>
              <strong>{formatTime(day?.first_login_time)}</strong>
            </div>
            <div className="summary-tile">
              <span>Last Logout</span>
              <strong>{formatTime(day?.last_logout_time)}</strong>
            </div>
            <div className="summary-tile">
              <span>Sessions</span>
              <strong>{day?.session_count ?? "—"}</strong>
            </div>
            <div className="summary-tile">
              <span>Active Time</span>
              <strong>{formatDuration(displaySeconds)}</strong>
            </div>
          </div>
          <div className="dash-mix">
            <div className="row-between">
              <span>Active</span>
              <strong>{formatDuration(displaySeconds)}</strong>
            </div>
            <div className="bar bar-active">
              <span style={{ width: `${barWidth(day?.total_active_seconds, day)}%` }} />
            </div>
            <div className="row-between">
              <span>Idle</span>
              <strong>{formatDuration(day?.total_idle_seconds)}</strong>
            </div>
            <div className="bar bar-idle">
              <span style={{ width: `${barWidth(day?.total_idle_seconds, day)}%` }} />
            </div>
            <div className="row-between">
              <span>Locked</span>
              <strong>{formatDuration(day?.total_locked_seconds)}</strong>
            </div>
            <div className="bar bar-locked">
              <span style={{ width: `${barWidth(day?.total_locked_seconds, day)}%` }} />
            </div>
          </div>
        </article>

        <DeviceStatusCard live={live} deviceName={deviceName === "—" ? undefined : deviceName} />
      </section>

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
    </div>
  );
}
