import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listDepartments, listEmployees, listTeams } from "../services/people.js";

export default function EmployeeListPage() {
  const [employees, setEmployees] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [teams, setTeams] = useState([]);
  const [search, setSearch] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [teamId, setTeamId] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  function load() {
    const params = {};
    if (search) params.search = search;
    if (departmentId) params.department_id = departmentId;
    if (teamId) params.team_id = teamId;
    if (status) params.employment_status = status;
    listEmployees(params)
      .then((response) => setEmployees(response.data))
      .catch((err) => setError(err.response?.data?.error?.message || "Unable to load employees"));
  }

  useEffect(() => {
    load();
    listDepartments().then((response) => setDepartments(response.data));
    listTeams().then((response) => setTeams(response.data));
  }, []);

  return (
    <section className="card">
      <div className="row-between">
        <h1>Employees</h1>
        <Link to="/employees/new">Create employee</Link>
      </div>
      <form
        className="filters"
        onSubmit={(event) => {
          event.preventDefault();
          load();
        }}
      >
        <input placeholder="Search" value={search} onChange={(event) => setSearch(event.target.value)} />
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
        <button type="submit">Filter</button>
      </form>
      {error && <p className="error">{error}</p>}
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Email</th>
            <th>Team</th>
            <th>Status</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {employees.map((employee) => (
            <tr key={employee.id}>
              <td>{employee.employee_code}</td>
              <td>
                {employee.first_name} {employee.last_name}
              </td>
              <td>{employee.email}</td>
              <td>{employee.team_name || "—"}</td>
              <td>{employee.employment_status}</td>
              <td>
                <Link to={`/employees/${employee.id}`}>View</Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
