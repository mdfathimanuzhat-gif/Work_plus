import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import AttendanceSummary from "../components/AttendanceSummary.jsx";
import Avatar from "../components/Avatar.jsx";
import LoadingState from "../components/LoadingState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { getEmployeeAttendance } from "../services/attendance.js";
import { deactivateEmployee, getEmployee } from "../services/people.js";
import { displayName, todayIso, userMessage } from "../utils/format.js";

export default function EmployeeDetailPage() {
  const { employeeId } = useParams();
  const [employee, setEmployee] = useState(null);
  const [day, setDay] = useState(null);
  const [error, setError] = useState("");
  const [confirm, setConfirm] = useState(false);

  useEffect(() => {
    getEmployee(employeeId)
      .then((response) => setEmployee(response.data))
      .catch((err) => setError(userMessage(err, "Unable to load employee")));
    getEmployeeAttendance(employeeId, todayIso())
      .then((response) => setDay(response.data))
      .catch(() => setDay(null));
  }, [employeeId]);

  async function handleDeactivate() {
    try {
      await deactivateEmployee(employeeId);
      const response = await getEmployee(employeeId);
      setEmployee(response.data);
      setConfirm(false);
    } catch (err) {
      setError(userMessage(err, "Unable to deactivate"));
    }
  }

  if (!employee) return error ? <div className="alert alert-error">{error}</div> : <LoadingState />;

  return (
    <div className="stack">
      <PageHeader
        title={displayName(employee)}
        subtitle={employee.employee_code}
        actions={
          <>
            <Link className="btn btn-secondary" to="/employees">
              Back
            </Link>
            <Link className="btn" to={`/employees/${employee.id}/edit`}>
              Edit
            </Link>
            <button className="btn btn-danger" type="button" onClick={() => setConfirm(true)}>
              Deactivate
            </button>
          </>
        }
      />
      {error ? <div className="alert alert-error">{error}</div> : null}
      {confirm ? (
        <article className="card">
          <p>Deactivate this employee account?</p>
          <div className="row">
            <button className="btn btn-danger" type="button" onClick={handleDeactivate}>
              Confirm deactivate
            </button>
            <button className="btn btn-secondary" type="button" onClick={() => setConfirm(false)}>
              Cancel
            </button>
          </div>
        </article>
      ) : null}
      <article className="card">
        <div className="person" style={{ gap: "1rem", marginBottom: "1rem" }}>
          <Avatar first={employee.first_name} last={employee.last_name} size="lg" />
          <div>
            <div className="row">
              <StatusBadge status={employee.employment_status} />
              <span className="badge badge-muted">{employee.account_status || "—"}</span>
            </div>
            <p className="muted">{employee.email}</p>
          </div>
        </div>
        <dl className="details">
          <dt>Phone</dt>
          <dd>{employee.phone || "—"}</dd>
          <dt>Department</dt>
          <dd>{employee.department_name || "—"}</dd>
          <dt>Team</dt>
          <dd>{employee.team_name || "—"}</dd>
          <dt>Reporting team lead</dt>
          <dd>{employee.manager_name || "—"}</dd>
          <dt>Joining date</dt>
          <dd>{employee.joining_date || "—"}</dd>
          <dt>Roles</dt>
          <dd>{employee.roles?.join(", ") || "—"}</dd>
        </dl>
      </article>
      <AttendanceSummary day={day} />
    </div>
  );
}
