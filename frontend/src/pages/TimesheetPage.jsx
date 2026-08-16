import EmptyState from "../components/EmptyState.jsx";
import PageHeader from "../components/PageHeader.jsx";

export default function TimesheetPage() {
  return (
    <div className="stack">
      <PageHeader title="Timesheet" subtitle="Daily work descriptions and approvals are not enabled yet." />
      <article className="card">
        <EmptyState title="Timesheets coming later" message="This module is reserved for a later phase. Attendance tracking remains available." />
      </article>
    </div>
  );
}
