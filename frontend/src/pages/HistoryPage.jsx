import { useCallback, useEffect, useMemo, useState } from "react";

import ActivityTimeline from "../components/ActivityTimeline.jsx";
import EmptyState from "../components/EmptyState.jsx";
import { Icon } from "../components/icons.jsx";
import LoadingState from "../components/LoadingState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import { getMyAttendanceDay } from "../services/attendance.js";
import { formatTime, todayIso, userMessage } from "../utils/format.js";
import { timelineFromAttendanceDay } from "../utils/timeline.js";

const EVENT_FILTERS = [
  { value: "ALL", label: "All types" },
  { value: "WINDOWS_LOGIN", label: "Windows Login" },
  { value: "WINDOWS_LOGOUT", label: "Windows Logout" },
  { value: "SYSTEM_LOCK", label: "System Lock" },
  { value: "SYSTEM_UNLOCK", label: "System Unlock" },
  { value: "IDLE_START", label: "Idle Start" },
  { value: "IDLE_END", label: "Idle End" },
  { value: "SYSTEM_SLEEP", label: "System Sleep" },
  { value: "SYSTEM_WAKE", label: "System Wake" },
  { value: "SYSTEM_SHUTDOWN", label: "Shutdown" },
  { value: "SYSTEM_RESTART", label: "Restart" },
];

export default function HistoryPage() {
  const [date, setDate] = useState(todayIso());
  const [type, setType] = useState("ALL");
  const [day, setDay] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    setLoading(true);
    try {
      setDay(await getMyAttendanceDay(date));
    } catch (err) {
      setError(userMessage(err, "We couldn't load activity history."));
      setDay(null);
    } finally {
      setLoading(false);
    }
  }, [date]);

  useEffect(() => {
    load();
  }, [load]);

  const items = useMemo(() => {
    const all = timelineFromAttendanceDay(day);
    if (type === "ALL") return all;
    return all.filter((item) => String(item.type || "").toUpperCase() === type);
  }, [day, type]);

  return (
    <div className="stack">
      <PageHeader
        title="Activity History"
        subtitle="Derived from daily sessions and attendance notes. A raw event feed is not available from the current API."
      />

      <div className="filters">
        <label className="label">
          Date
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </label>
        <label className="label" style={{ minWidth: 200 }}>
          Event type
          <select value={type} onChange={(e) => setType(e.target.value)}>
            {EVENT_FILTERS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error ? <div className="alert alert-error">{error}</div> : null}

      <article className="card">
        {loading ? (
          <LoadingState kind="timeline" />
        ) : items.length ? (
          <div className="stack">
            <ActivityTimeline items={items} />
            <div className="table-wrap">
              <table className="data">
                <thead>
                  <tr>
                    <th>Event</th>
                    <th>Timestamp</th>
                    <th>Device</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {items.map((item) => (
                    <tr key={item.id}>
                      <td>{item.label}</td>
                      <td>{formatTime(item.time)}</td>
                      <td>—</td>
                      <td>{item.detail || item.type || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : (
          <EmptyState
            icon={<Icon name="activity" />}
            title="No activity recorded yet."
            body="Historical raw events are not exposed by the API. This view uses session and anomaly data for the selected date."
          />
        )}
      </article>
    </div>
  );
}
