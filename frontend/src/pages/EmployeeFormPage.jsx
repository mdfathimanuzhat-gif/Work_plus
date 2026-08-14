import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { createEmployee, getEmployee, listDepartments, listEmployees, listTeams, updateEmployee } from "../services/people.js";

const empty = {
  employee_code: "",
  first_name: "",
  last_name: "",
  email: "",
  phone: "",
  department_id: "",
  team_id: "",
  manager_id: "",
  joining_date: "",
  employment_status: "ACTIVE",
  role: "EMPLOYEE",
  password: "",
};

export default function EmployeeFormPage() {
  const { employeeId } = useParams();
  const navigate = useNavigate();
  const isEdit = Boolean(employeeId);
  const [form, setForm] = useState(empty);
  const [departments, setDepartments] = useState([]);
  const [teams, setTeams] = useState([]);
  const [managers, setManagers] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    listDepartments().then((response) => setDepartments(response.data));
    listTeams().then((response) => setTeams(response.data));
    listEmployees().then((response) => setManagers(response.data));
    if (isEdit) {
      getEmployee(employeeId).then((response) => {
        const employee = response.data;
        setForm({
          employee_code: employee.employee_code,
          first_name: employee.first_name,
          last_name: employee.last_name,
          email: employee.email,
          phone: employee.phone || "",
          department_id: employee.department_id || "",
          team_id: employee.team_id || "",
          manager_id: employee.manager_id || "",
          joining_date: employee.joining_date || "",
          employment_status: employee.employment_status,
          role: employee.roles?.[0] || "EMPLOYEE",
          password: "",
        });
      });
    }
  }, [employeeId, isEdit]);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    const payload = {
      ...form,
      department_id: form.department_id || null,
      team_id: form.team_id || null,
      manager_id: form.manager_id || null,
      joining_date: form.joining_date || null,
      phone: form.phone || null,
    };
    try {
      if (isEdit) {
        const { employee_code, password, ...updatePayload } = payload;
        await updateEmployee(employeeId, updatePayload);
        navigate(`/employees/${employeeId}`);
      } else {
        if (!payload.password) delete payload.password;
        const created = await createEmployee(payload);
        navigate(`/employees/${created.data.id}`);
      }
    } catch (err) {
      setError(err.response?.data?.error?.message || "Unable to save employee");
    }
  }

  return (
    <section className="card">
      <h1>{isEdit ? "Edit employee" : "Create employee"}</h1>
      <form className="stack" onSubmit={handleSubmit}>
        <label>
          Employee ID
          <input value={form.employee_code} onChange={(event) => updateField("employee_code", event.target.value)} required disabled={isEdit} />
        </label>
        <label>
          First name
          <input value={form.first_name} onChange={(event) => updateField("first_name", event.target.value)} required />
        </label>
        <label>
          Last name
          <input value={form.last_name} onChange={(event) => updateField("last_name", event.target.value)} />
        </label>
        <label>
          Email
          <input type="email" value={form.email} onChange={(event) => updateField("email", event.target.value)} required />
        </label>
        <label>
          Phone
          <input value={form.phone} onChange={(event) => updateField("phone", event.target.value)} />
        </label>
        <label>
          Department
          <select value={form.department_id} onChange={(event) => updateField("department_id", event.target.value)}>
            <option value="">None</option>
            {departments.map((department) => (
              <option key={department.id} value={department.id}>
                {department.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Team
          <select value={form.team_id} onChange={(event) => updateField("team_id", event.target.value)}>
            <option value="">None</option>
            {teams.map((team) => (
              <option key={team.id} value={team.id}>
                {team.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Reporting Team Lead
          <select value={form.manager_id} onChange={(event) => updateField("manager_id", event.target.value)}>
            <option value="">None</option>
            {managers.map((manager) => (
              <option key={manager.id} value={manager.id}>
                {manager.first_name} {manager.last_name} ({manager.employee_code})
              </option>
            ))}
          </select>
        </label>
        <label>
          Joining date
          <input type="date" value={form.joining_date} onChange={(event) => updateField("joining_date", event.target.value)} />
        </label>
        <label>
          Employment status
          <select value={form.employment_status} onChange={(event) => updateField("employment_status", event.target.value)}>
            <option value="ACTIVE">ACTIVE</option>
            <option value="INACTIVE">INACTIVE</option>
            <option value="ON_LEAVE">ON_LEAVE</option>
            <option value="TERMINATED">TERMINATED</option>
          </select>
        </label>
        <label>
          Role
          <select value={form.role} onChange={(event) => updateField("role", event.target.value)}>
            <option value="EMPLOYEE">EMPLOYEE</option>
            <option value="TEAM_LEAD">TEAM_LEAD</option>
            <option value="HR">HR</option>
            <option value="ADMIN">ADMIN</option>
          </select>
        </label>
        {!isEdit && (
          <label>
            Temporary password
            <input type="password" value={form.password} onChange={(event) => updateField("password", event.target.value)} />
          </label>
        )}
        {error && <p className="error">{error}</p>}
        <div className="row">
          <button type="submit">Save</button>
          <Link to="/employees">Cancel</Link>
        </div>
      </form>
    </section>
  );
}
