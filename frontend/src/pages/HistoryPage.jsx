import { useCallback, useEffect, useMemo, useState } from "react";

import ActivityTimeline from "../components/ActivityTimeline.jsx";
import EmptyState from "../components/EmptyState.jsx";
import { Icon } from "../components/icons.jsx";
import LoadingState from "../components/LoadingState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import { getEvents } from "../services/attendance.js";
import { formatTime, todayIso, userMessage } from "../utils/format.js";
import { eventLabel } from "../utils/timeline.js";

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

const FILTER_MATCHES = {
  WINDOWS_LOGIN: ["WINDOWS_LOGIN", "LOGIN"],
  WINDOWS_LOGOUT: ["WINDOWS_LOGOUT", "LOGOUT"],
  SYSTEM_LOCK: ["SYSTEM_LOCK", "LOCK"],
  SYSTEM_UNLOCK: ["SYSTEM_UNLOCK", "UNLOCK"],
  SYSTEM_SLEEP: ["SYSTEM_SLEEP", "SLEEP"],
  SYSTEM_WAKE: ["SYSTEM_WAKE", "WAKE"],
  SYSTEM_SHUTDOWN: ["SYSTEM_SHUTDOWN", "SHUTDOWN"],
  SYSTEM_RESTART: ["SYSTEM_RESTART", "RESTART"],
  IDLE_START: ["IDLE_START"],
  IDLE_END: ["IDLE_END"],
};

function matchesFilter(eventType, filter) {
  if (filter === "ALL") return true;
  const type = String(eventType || "").toUpperCase();
  const aliases = FILTER_MATCHES[filter] || [filter];
  return aliases.includes(type);
}

function toTimelineItem(event, index) {
  const type = event.event_type;
  return {
    id: `${event.event_timestamp}-${type}-${event.device_id || index}`,
    type,
    label: eventLabel(type),
    time: event.event_timestamp,
    detail: event.device_name || null,
  };
}

export default function HistoryPage() {
  const [date, setDate] = useState(todayIso());
  const [type, setType] = useState("ALL");
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    setLoading(true);
    try {
      setEvents(await getEvents(date));
    } catch (err) {
      setError(userMessage(err, "We couldn't load activity history."));
      setEvents([]);
    } finally {
      setLoading(false);
    }
  }, [date]);

  useEffect(() => {
    load();
  }, [load]);

  const items = useMemo(() => {
    return events.filter((event) => matchesFilter(event.event_type, type)).map(toTimelineItem);
  }, [events, type]);

  return (
    <div className="stack">
      <PageHeader
        title="Activity History"
        subtitle="Lock, unlock, idle, and session events from the WorkPulse Agent."
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
                      <td>{item.detail || "—"}</td>
                      <td>{item.type || "—"}</td>
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
            body="Events from the WorkPulse Agent for this date will appear here."
          />
        )}
      </article>
    </div>
  );
}
