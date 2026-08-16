import { useEffect, useMemo, useState } from "react";

import DataTable from "../components/DataTable.jsx";
import { Icon } from "../components/icons.jsx";
import LoadingState from "../components/LoadingState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { getMyAttendance } from "../services/attendance.js";
import { formatDate, formatDuration, formatTime, userMessage } from "../utils/format.js";

export default function TimesheetPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [query, setQuery] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const params = {};
        if (from) params.start = from;
        if (to) params.end = to;
        const list = await getMyAttendance(params);
        if (!cancelled) setRows(Array.isArray(list.data) ? list.data : []);
      } catch (err) {
        if (!cancelled) setError(userMessage(err, "We couldn't load timesheet data."));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [from, to]);

  const filtered = useMemo(() => {
    const q = query.trim();
    if (!q) return rows;
    return rows.filter((row) => String(row.attendance_date).includes(q));
  }, [rows, query]);

  return (
    <div className="stack">
      <PageHeader
        title="Timesheet"
        subtitle="Daily working time from processed attendance records"
        actions={
          <button type="button" className="btn btn-secondary" disabled title="Export is not available yet">
            <Icon name="download" size={16} />
            Export
          </button>
        }
      />

      <div className="filters">
        <label className="label">
          From
          <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        </label>
        <label className="label">
          To
          <input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        </label>
        <label className="label" style={{ flex: 1, minWidth: 180 }}>
          Search
          <span className="search-field">
            <Icon name="search" size={16} />
            <input
              placeholder="Filter by date (YYYY-MM-DD)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
            />
          </span>
        </label>
      </div>

      {error ? <div className="alert alert-error">{error}</div> : null}

      {loading ? (
        <LoadingState kind="table" />
      ) : (
        <article className="card">
          <DataTable
            columns={[
              { key: "date", header: "Date", render: (row) => formatDate(row.attendance_date) },
              { key: "login", header: "Login", render: (row) => formatTime(row.first_login_time) },
              { key: "logout", header: "Logout", render: (row) => formatTime(row.last_logout_time) },
              { key: "active", header: "Active Time", render: (row) => formatDuration(row.total_active_seconds) },
              { key: "idle", header: "Idle Time", render: (row) => formatDuration(row.total_idle_seconds) },
              { key: "locked", header: "Locked Time", render: (row) => formatDuration(row.total_locked_seconds) },
              {
                key: "total",
                header: "Total Time",
                render: (row) => formatDuration(row.total_session_seconds),
              },
              {
                key: "status",
                header: "Status",
                render: (row) => (
                  <StatusBadge status={row.status} />
                ),
              },
            ]}
            rows={filtered}
            emptyTitle="No timesheet rows in this range."
            emptyBody="Attendance days will appear here once the agent has synced events."
          />
        </article>
      )}
    </div>
  );
}
