import { useEffect, useState } from "react";
import { createTeam, listDepartments, listEmployees, listTeams, updateTeam } from "../services/people.js";

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
      .catch((err) => setError(err.response?.data?.error?.message || "Unable to load teams"));
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
      setError(err.response?.data?.error?.message || "Unable to create team");
    }
  }

  async function assignLead(teamId, leadId) {
    await updateTeam(teamId, { team_lead_id: leadId || null });
    load();
  }

  return (
    <section className="card">
      <h1>Teams</h1>
      <form className="filters" onSubmit={handleCreate}>
        <input placeholder="Team name" value={name} onChange={(event) => setName(event.target.value)} required />
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
        <button type="submit">Create</button>
      </form>
      {error && <p className="error">{error}</p>}
      <table>
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
              <td>{team.department_name || "—"}</td>
              <td>{team.team_lead_name || "—"}</td>
              <td>
                <select
                  defaultValue={team.team_lead_id || ""}
                  onChange={(event) => assignLead(team.id, event.target.value)}
                >
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
    </section>
  );
}
