import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader.jsx";
import StatCard from "../components/StatCard.jsx";
import { createTeam, listDepartments, listEmployees, listTeams, updateTeam } from "../services/people.js";
import { apiError } from "../utils/format.js";

export default function TeamsPage() {
  const [teams, setTeams] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [employees, setEmployees] = useState([]);
  const [name, setName] = useState("");
  const [departmentId, setDepartmentId] = useState("");
  const [teamLeadId, setTeamLeadId] = useState("");
  const [error, setError] = useState("");

  function load() {
    listTeams()
      .then((response) => setTeams(response.data))
      .catch((err) => setError(apiError(err, "Unable to load teams")));
  }

  useEffect(() => {
    load();
    listDepartments().then((response) => setDepartments(response.data));
    listEmployees().then((response) => setEmployees(response.data));
  }, []);

  async function handleCreate(event) {
    event.preventDefault();
    setError("");
    try {
      await createTeam({
        name,
        department_id: departmentId || null,
        team_lead_id: teamLeadId || null,
      });
      setName("");
      setDepartmentId("");
      setTeamLeadId("");
      load();
    } catch (err) {
      setError(apiError(err, "Unable to create team"));
    }
  }

  async function assignLead(teamId, leadId) {
    await updateTeam(teamId, { team_lead_id: leadId || null });
    load();
  }

  return (
    <div className="stack">
      <PageHeader title="Teams" subtitle="Team leads and department assignment." />
      <section className="grid grid-3">
        <StatCard icon="users" label="Teams" value={teams.length} />
        <StatCard icon="building" label="Departments linked" value={new Set(teams.map((team) => team.department_id).filter(Boolean)).size} />
        <StatCard icon="user" label="With lead" value={teams.filter((team) => team.team_lead_id).length} />
      </section>
      <article className="card">
        <form className="filters" onSubmit={handleCreate}>
          <input className="input" placeholder="Team name" value={name} onChange={(event) => setName(event.target.value)} required />
          <select value={departmentId} onChange={(event) => setDepartmentId(event.target.value)}>
            <option value="">Department</option>
            {departments.map((department) => (
              <option key={department.id} value={department.id}>
                {department.name}
              </option>
            ))}
          </select>
          <select value={teamLeadId} onChange={(event) => setTeamLeadId(event.target.value)}>
            <option value="">Team lead</option>
            {employees.map((employee) => (
              <option key={employee.id} value={employee.id}>
                {employee.first_name} {employee.last_name}
              </option>
            ))}
          </select>
          <button className="btn" type="submit">
            Create
          </button>
        </form>
        {error ? <div className="alert alert-error">{error}</div> : null}
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Name</th>
                <th>Department</th>
                <th>Team lead</th>
                <th>Assign lead</th>
              </tr>
            </thead>
            <tbody>
              {teams.map((team) => (
                <tr key={team.id}>
                  <td>{team.name}</td>
                  <td>
                    <span className="badge badge-primary">{team.department_name || "—"}</span>
                  </td>
                  <td>{team.team_lead_name || "—"}</td>
                  <td>
                    <select defaultValue={team.team_lead_id || ""} onChange={(event) => assignLead(team.id, event.target.value)}>
                      <option value="">None</option>
                      {employees.map((employee) => (
                        <option key={employee.id} value={employee.id}>
                          {employee.first_name} {employee.last_name}
                        </option>
                      ))}
                    </select>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </div>
  );
}
