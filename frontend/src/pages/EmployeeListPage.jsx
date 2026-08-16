import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import Avatar from "../components/Avatar.jsx";
import DataTable from "../components/DataTable.jsx";
import { Icon } from "../components/icons.jsx";
import LoadingState from "../components/LoadingState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { listDepartments, listEmployees, listTeams } from "../services/people.js";
import { displayName, userMessage } from "../utils/format.js";

export default function EmployeeListPage() {
  const [employees, setEmployees] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [teams, setTeams] = useState([]);
  const [search, setSearch] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [teamId, setTeamId] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  function load() {
    const params = {};
    if (search) params.search = search;
    if (departmentId) params.department_id = departmentId;
    if (teamId) params.team_id = teamId;
    if (status) params.employment_status = status;
    setLoading(true);
    listEmployees(params)
      .then((response) => setEmployees(response.data))
      .catch((err) => setError(userMessage(err, "Unable to load employees")))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
    listDepartments().then((response) => setDepartments(response.data)).catch(() => {});
    listTeams().then((response) => setTeams(response.data)).catch(() => {});
  }, []);

  const activeCount = employees.filter((row) => row.employment_status === "ACTIVE").length;

  return (
    <div className="stack">
      <PageHeader
        title="Employees"
        subtitle="Directory for your organization."
        actions={
          <Link className="btn" to="/employees/new">
            <Icon name="plus" size={16} />
            Add employee
          </Link>
        }
      />
      <section className="grid grid-3">
        <StatMini label="Total employees" value={employees.length} />
        <StatMini label="Active" value={activeCount} />
        <StatMini label="Other statuses" value={Math.max(0, employees.length - activeCount)} />
      </section>
      <article className="card">
        <form
          className="filters"
          onSubmit={(event) => {
            event.preventDefault();
            load();
          }}
        >
          <span className="search-field" style={{ flex: 1, minWidth: 200 }}>
            <Icon name="search" size={16} />
            <input placeholder="Search name or email" value={search} onChange={(event) => setSearch(event.target.value)} />
          </span>
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
        {loading ? (
          <LoadingState kind="table" />
        ) : (
          <DataTable
            columns={[
              {
                key: "employee",
                header: "Employee",
                render: (employee) => (
                  <div className="person">
                    <Avatar first={employee.first_name} last={employee.last_name} />
                    <div>
                      <strong>{displayName(employee)}</strong>
                      <div className="muted">{employee.email}</div>
                    </div>
                  </div>
                ),
              },
              { key: "code", header: "ID", render: (employee) => employee.employee_code },
              {
                key: "dept",
                header: "Department",
                render: (employee) => <span className="badge badge-primary">{employee.department_name || "—"}</span>,
              },
              {
                key: "team",
                header: "Team",
                render: (employee) => <span className="badge badge-muted">{employee.team_name || "—"}</span>,
              },
              {
                key: "status",
                header: "Status",
                render: (employee) => <StatusBadge status={employee.employment_status} />,
              },
              {
                key: "actions",
                header: "Actions",
                render: (employee) => (
                  <div className="row">
                    <Link className="btn btn-ghost" to={`/employees/${employee.id}`}>
                      View
                    </Link>
                    <Link className="btn btn-secondary" to={`/employees/${employee.id}/edit`}>
                      Edit
                    </Link>
                  </div>
                ),
              },
            ]}
            rows={employees}
            emptyTitle="No employees"
            emptyBody="Try a different filter or create an employee."
          />
        )}
      </article>
    </div>
  );
}

function StatMini({ label, value }) {
  return (
    <article className="card">
      <p className="muted" style={{ margin: 0 }}>{label}</p>
      <p style={{ fontSize: 28, fontWeight: 730, margin: "6px 0 0", letterSpacing: "-0.04em" }}>{value}</p>
    </article>
  );
}
