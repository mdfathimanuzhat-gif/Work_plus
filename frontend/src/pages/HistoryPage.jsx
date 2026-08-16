import { useEffect, useState } from "react";
import EmptyState from "../components/EmptyState.jsx";
import LoadingState from "../components/LoadingState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { getMyAttendance } from "../services/attendance.js";
import { apiError, formatDuration, formatTime, todayIso } from "../utils/format.js";

export default function HistoryPage() {
  const [start, setStart] = useState(shiftDays(todayIso(), -13));
  const [end, setEnd] = useState(todayIso());
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    getMyAttendance({ start, end })
      .then((response) => {
        if (!cancelled) setRows(response.data || []);
      })
      .catch((err) => {
        if (!cancelled) setError(apiError(err, "Unable to load history"));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [start, end]);

  return (
    <div className="stack">
      <PageHeader title="History" subtitle="Attendance records from the calculation engine." />
      <form className="filters" onSubmit={(event) => event.preventDefault()}>
        <input className="input" type="date" value={start} onChange={(event) => setStart(event.target.value)} />
        <input className="input" type="date" value={end} onChange={(event) => setEnd(event.target.value)} />
      </form>
      {error ? <div className="alert alert-error">{error}</div> : null}
      <article className="card">
        {loading ? <LoadingState /> : null}
        {!loading && !rows.length ? <EmptyState title="No records" message="There is no attendance history in this range." /> : null}
        {rows.length ? (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Status</th>
                  <th>First login</th>
                  <th>Last logout</th>
                  <th>Active</th>
                  <th>Idle</th>
                  <th>Locked</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id}>
                    <td>{row.attendance_date}</td>
                    <td>
                      <StatusBadge status={row.status} />
                    </td>
                    <td>{formatTime(row.first_login_time)}</td>
                    <td>{formatTime(row.last_logout_time)}</td>
                    <td>{formatDuration(row.total_active_seconds)}</td>
                    <td>{formatDuration(row.total_idle_seconds)}</td>
                    <td>{formatDuration(row.total_locked_seconds)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </article>
    </div>
  );
}

function shiftDays(iso, days) {
  const date = new Date(`${iso}T00:00:00`);
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}
