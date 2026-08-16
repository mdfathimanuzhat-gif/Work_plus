import { useCallback, useEffect, useState } from "react";

import DataTable from "../components/DataTable.jsx";
import LoadingState from "../components/LoadingState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import { listTeamTimesheetEntries, reviewTimesheetEntry } from "../services/timesheet.js";
import { formatDate, userMessage } from "../utils/format.js";

export default function ApprovalsPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [activeId, setActiveId] = useState("");
  const [decision, setDecision] = useState("");
  const [comments, setComments] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    setError("");
    try {
      const list = await listTeamTimesheetEntries();
      setRows(Array.isArray(list.data) ? list.data : []);
    } catch (err) {
      setError(userMessage(err, "We couldn't load pending timesheets."));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function openReview(entryId, status) {
    setActiveId(entryId);
    setDecision(status);
    setComments("");
  }

  function cancelReview() {
    setActiveId("");
    setDecision("");
    setComments("");
  }

  async function confirmReview() {
    if (!activeId || !decision) return;
    setSaving(true);
    setError("");
    try {
      await reviewTimesheetEntry(activeId, {
        status: decision,
        comments: comments.trim() || null,
      });
      cancelReview();
      setLoading(true);
      await load();
    } catch (err) {
      setError(userMessage(err, "We couldn't record this review."));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="stack">
      <PageHeader
        title="Approvals"
        subtitle="Review submitted timesheet entries from your team or organization. The API returns employee ID, not a display name."
      />

      {error ? <div className="alert alert-error">{error}</div> : null}

      {loading ? (
        <LoadingState kind="table" />
      ) : (
        <article className="card">
          <DataTable
            columns={[
              {
                key: "employee",
                header: "Employee",
                render: (row) => (
                  <div>
                    <strong>{row.employee_name || "Employee"}</strong>
                    <div className="muted">{row.employee_id}</div>
                  </div>
                ),
              },
              { key: "date", header: "Date", render: (row) => formatDate(row.date) },
              { key: "project", header: "Project" },
              { key: "task", header: "Task" },
              { key: "hours", header: "Hours", render: (row) => row.hours ?? "—" },
              {
                key: "description",
                header: "Description",
                render: (row) => row.description || "—",
              },
              {
                key: "actions",
                header: "",
                render: (row) => (
                  <div className="row">
                    <button type="button" className="btn" onClick={() => openReview(row.id, "approved")}>
                      Approve
                    </button>
                    <button type="button" className="btn btn-danger" onClick={() => openReview(row.id, "rejected")}>
                      Reject
                    </button>
                  </div>
                ),
              },
            ]}
            rows={rows}
            emptyTitle="No pending timesheets to review."
            emptyBody="Submitted entries from your reports will appear here."
          />

          {activeId ? (
            <div className="review-panel">
              <p className="muted" style={{ margin: 0 }}>
                {decision === "approved" ? "Approve" : "Reject"} this timesheet. Comments are optional.
              </p>
              <label className="label" style={{ marginTop: "0.75rem" }}>
                Comments
                <textarea className="input" rows={3} value={comments} onChange={(e) => setComments(e.target.value)} />
              </label>
              <div className="row" style={{ marginTop: "0.75rem" }}>
                <button type="button" className={decision === "rejected" ? "btn btn-danger" : "btn"} disabled={saving} onClick={confirmReview}>
                  {saving ? "Saving…" : "Confirm"}
                </button>
                <button type="button" className="btn btn-secondary" disabled={saving} onClick={cancelReview}>
                  Cancel
                </button>
              </div>
            </div>
          ) : null}
        </article>
      )}
    </div>
  );
}
