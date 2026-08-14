import { useEffect, useState } from "react";
import { createDepartment, listDepartments, updateDepartment } from "../services/people.js";

export default function DepartmentsPage() {
  const [departments, setDepartments] = useState([]);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");

  function load() {
    listDepartments()
      .then((response) => setDepartments(response.data))
      .catch((err) => setError(err.response?.data?.error?.message || "Unable to load departments"));
  }

  useEffect(() => {
    load();
  }, []);

  async function handleCreate(event) {
    event.preventDefault();
    setError("");
    try {
      await createDepartment({ name, code });
      setName("");
      setCode("");
      load();
    } catch (err) {
      setError(err.response?.data?.error?.message || "Unable to create department");
    }
  }

  async function toggleActive(department) {
    await updateDepartment(department.id, { is_active: !department.is_active });
    load();
  }

  return (
    <section className="card">
      <h1>Departments</h1>
      <form className="filters" onSubmit={handleCreate}>
        <input placeholder="Name" value={name} onChange={(event) => setName(event.target.value)} required />
        <input placeholder="Code" value={code} onChange={(event) => setCode(event.target.value)} required />
        <button type="submit">Create</button>
      </form>
      {error && <p className="error">{error}</p>}
      <table>
        <thead>
          <tr>
            <th>Code</th>
            <th>Name</th>
            <th>Active</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {departments.map((department) => (
            <tr key={department.id}>
              <td>{department.code}</td>
              <td>{department.name}</td>
              <td>{department.is_active ? "Yes" : "No"}</td>
              <td>
                <button type="button" onClick={() => toggleActive(department)}>
                  {department.is_active ? "Deactivate" : "Activate"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
