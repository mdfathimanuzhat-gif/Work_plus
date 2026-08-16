import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import Avatar from "../components/Avatar.jsx";
import EmptyState from "../components/EmptyState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { listDepartments, listEmployees, listTeams } from "../services/people.js";
import { apiError, displayName } from "../utils/format.js";

export default function EmployeeListPage() {
  const [employees, setEmployees] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [teams, setTeams] = useState([]);
  const [search, setSearch] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [teamId, setTeamId] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [menuFor, setMenuFor] = useState(null);

  function load() {
    const params = {};
    if (search) params.search = search;
    if (departmentId) params.department_id = departmentId;
    if (teamId) params.team_id = teamId;
    if (status) params.employment_status = status;
    listEmployees(params)
      .then((response) => setEmployees(response.data))
      .catch((err) => setError(apiError(err, "Unable to load employees")));
  }

  useEffect(() => {
    load();
    listDepartments().then((response) => setDepartments(response.data));
    listTeams().then((response) => setTeams(response.data));
  }, []);

  return (
    <div className="stack">
      <PageHeader
        title="Employees"
        subtitle="Directory for your organization."
        actions={
          <Link className="btn" to="/employees/new">
            Add employee
          </Link>
        }
      />
      <article className="card">
        <form
          className="filters"
          onSubmit={(event) => {
            event.preventDefault();
            load();
          }}
        >
          <input className="input" placeholder="Search" value={search} onChange={(event) => setSearch(event.target.value)} />
          <select value={departmentId} onChange={(event) => setDepartmentId(event.target.value)}>
            <option value="">All departments</option>
            {departments.map((department) => (
              <option key={department.id} value={department.id}>
                {department.name}
              </option>
            ))}
          </select>
          <select value={teamId} onChange={(event) => setTeamId(event.target.value)}>
            <option value="">All teams</option>
            {teams.map((team) => (
              <option key={team.id} value={team.id}>
                {team.name}
              </option>
            ))}
          </select>
          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">All statuses</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="INACTIVE">INACTIVE</option>
            <option value="ON_LEAVE">ON_LEAVE</option>
            <option value="TERMINATED">TERMINATED</option>
          </select>
          <button className="btn" type="submit">
            Filter
          </button>
        </form>
        {error ? <div className="alert alert-error">{error}</div> : null}
        {!employees.length ? <EmptyState title="No employees" message="Try a different filter or create an employee." /> : null}
        {employees.length ? (
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Employee</th>
                  <th>ID</th>
                  <th>Department</th>
                  <th>Team</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {employees.map((employee) => (
                  <tr key={employee.id}>
                    <td>
                      <div className="person">
                        <Avatar first={employee.first_name} last={employee.last_name} />
                        <div>
                          <strong>{displayName(employee)}</strong>
                          <div className="muted">{employee.email}</div>
                        </div>
                      </div>
                    </td>
                    <td>{employee.employee_code}</td>
                    <td>
                      <span className="badge badge-primary">{employee.department_name || "—"}</span>
                    </td>
                    <td>
                      <span className="badge badge-muted">{employee.team_name || "—"}</span>
                    </td>
                    <td>
                      <StatusBadge status={employee.employment_status} />
                    </td>
                    <td>
                      <div className={`dropdown ${menuFor === employee.id ? "open" : ""}`}>
                        <button type="button" className="btn btn-secondary" onClick={() => setMenuFor(menuFor === employee.id ? null : employee.id)}>
                          Actions
                        </button>
                        <div className="dropdown-menu">
                          <Link to={`/employees/${employee.id}`}>View</Link>
                          <Link to={`/employees/${employee.id}/edit`}>Edit</Link>
                        </div>
                      </div>
                    </td>
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
