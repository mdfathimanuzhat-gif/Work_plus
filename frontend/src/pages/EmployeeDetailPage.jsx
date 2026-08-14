import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { deactivateEmployee, getEmployee } from "../services/people.js";

export default function EmployeeDetailPage() {
  const { employeeId } = useParams();
  const navigate = useNavigate();
  const [employee, setEmployee] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getEmployee(employeeId)
      .then((response) => setEmployee(response.data))
      .catch((err) => setError(err.response?.data?.error?.message || "Unable to load employee"));
  }, [employeeId]);

  async function handleDeactivate() {
    if (!window.confirm("Deactivate this employee?")) {
      return;
    }
    try {
      await deactivateEmployee(employeeId);
      const response = await getEmployee(employeeId);
      setEmployee(response.data);
    } catch (err) {
      setError(err.response?.data?.error?.message || "Unable to deactivate");
    }
  }

  if (!employee) {
    return <p>{error || "Loading…"}</p>;
  }

  return (
    <section className="card">
      <div className="row-between">
        <h1>
          {employee.first_name} {employee.last_name}
        </h1>
        <div className="row">
          <Link to={`/employees/${employee.id}/edit`}>Edit</Link>
          <button type="button" onClick={handleDeactivate}>
            Deactivate
          </button>
          <button type="button" onClick={() => navigate("/employees")}>
            Back
          </button>
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      <dl className="details">
        <dt>Employee ID</dt>
        <dd>{employee.employee_code}</dd>
        <dt>Email</dt>
        <dd>{employee.email}</dd>
        <dt>Phone</dt>
        <dd>{employee.phone || "—"}</dd>
        <dt>Department</dt>
        <dd>{employee.department_name || "—"}</dd>
        <dt>Team</dt>
        <dd>{employee.team_name || "—"}</dd>
        <dt>Reporting Team Lead</dt>
        <dd>{employee.manager_name || "—"}</dd>
        <dt>Joining date</dt>
        <dd>{employee.joining_date || "—"}</dd>
        <dt>Employment status</dt>
        <dd>{employee.employment_status}</dd>
        <dt>Account status</dt>
        <dd>{employee.account_status}</dd>
        <dt>Roles</dt>
        <dd>{employee.roles.join(", ") || "—"}</dd>
      </dl>
    </section>
  );
}
