import { useCallback, useEffect, useState } from "react";

import DataTable from "../components/DataTable.jsx";
import LoadingState from "../components/LoadingState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { createTimesheetEntry, listMyTimesheetEntries, submitTimesheetEntry } from "../services/timesheet.js";
import { formatDate, todayIso, userMessage } from "../utils/format.js";

const emptyForm = {
  date: todayIso(),
  project: "",
  task: "",
  description: "",
  hours: "",
};

export default function TimesheetPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [formError, setFormError] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [submittingId, setSubmittingId] = useState("");

  const load = useCallback(async () => {
    setError("");
    const params = {};
    if (from) params.date_from = from;
    if (to) params.date_to = to;
    try {
      const list = await listMyTimesheetEntries(params);
      setRows(Array.isArray(list.data) ? list.data : []);
    } catch (err) {
      setError(userMessage(err, "We couldn't load your timesheet entries."));
    } finally {
      setLoading(false);
    }
  }, [from, to]);

  useEffect(() => {
    setLoading(true);
    load();
  }, [load]);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleCreate(event) {
    event.preventDefault();
    setFormError("");
    setSaving(true);
    try {
      await createTimesheetEntry({
        date: form.date,
        project: form.project.trim(),
        task: form.task.trim(),
        description: form.description.trim() || null,
        hours: form.hours,
      });
      setForm({ ...emptyForm, date: form.date || todayIso() });
      await load();
    } catch (err) {
      setFormError(userMessage(err, "We couldn't save this timesheet entry."));
    } finally {
      setSaving(false);
    }
  }

  async function handleSubmit(entryId) {
    setSubmittingId(entryId);
    setError("");
    try {
      await submitTimesheetEntry(entryId);
      await load();
    } catch (err) {
      setError(userMessage(err, "We couldn't submit this timesheet entry."));
    } finally {
      setSubmittingId("");
    }
  }

  return (
    <div className="stack">
      <PageHeader
        title="Timesheet"
        subtitle="Log project time, keep drafts, and submit entries for review."
      />

      <article className="card">
        <h2 className="card-title">New entry</h2>
        <form className="stack" onSubmit={handleCreate}>
          <div className="grid grid-2 form-grid">
            <label className="label">
              Date
              <input className="input" type="date" value={form.date} onChange={(e) => updateField("date", e.target.value)} required />
            </label>
            <label className="label">
              Hours
              <input
                className="input"
                type="number"
                min="0"
                max="9999.99"
                step="0.25"
                value={form.hours}
                onChange={(e) => updateField("hours", e.target.value)}
                required
              />
            </label>
            <label className="label">
              Project
              <input className="input" value={form.project} onChange={(e) => updateField("project", e.target.value)} required />
            </label>
            <label className="label">
              Task
              <input className="input" value={form.task} onChange={(e) => updateField("task", e.target.value)} required />
            </label>
            <label className="label" style={{ gridColumn: "1 / -1" }}>
              Description
              <textarea className="input" rows={3} value={form.description} onChange={(e) => updateField("description", e.target.value)} />
            </label>
          </div>
          {formError ? <div className="alert alert-error">{formError}</div> : null}
          <div className="row">
            <button className="btn" type="submit" disabled={saving}>
              {saving ? "Saving…" : "Save draft"}
            </button>
          </div>
        </form>
      </article>

      <div className="filters">
        <label className="label">
          From
          <input type="date" value={from} onChange={(e) => setFrom(e.target.value)} />
        </label>
        <label className="label">
          To
          <input type="date" value={to} onChange={(e) => setTo(e.target.value)} />
        </label>
      </div>

      {error ? <div className="alert alert-error">{error}</div> : null}

      {loading ? (
        <LoadingState kind="table" />
      ) : (
        <article className="card">
          <h2 className="card-title">My entries</h2>
          <DataTable
            columns={[
              { key: "date", header: "Date", render: (row) => formatDate(row.date) },
              { key: "project", header: "Project" },
              { key: "task", header: "Task" },
              { key: "hours", header: "Hours", render: (row) => row.hours ?? "—" },
              {
                key: "status",
                header: "Status",
                render: (row) => <StatusBadge status={row.status} />,
              },
              {
                key: "actions",
                header: "",
                render: (row) =>
                  row.status === "DRAFT" ? (
                    <button
                      type="button"
                      className="btn btn-secondary"
                      disabled={submittingId === row.id}
                      onClick={() => handleSubmit(row.id)}
                    >
                      {submittingId === row.id ? "Submitting…" : "Submit"}
                    </button>
                  ) : null,
              },
            ]}
            rows={rows}
            emptyTitle="No timesheet entries yet."
            emptyBody="Create a draft above to start tracking project time."
          />
        </article>
      )}
    </div>
  );
}
