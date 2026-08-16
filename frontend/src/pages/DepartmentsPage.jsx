import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader.jsx";
import StatCard from "../components/StatCard.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { createDepartment, listDepartments, updateDepartment } from "../services/people.js";
import { apiError } from "../utils/format.js";

export default function DepartmentsPage() {
  const [departments, setDepartments] = useState([]);
  const [name, setName] = useState("");
  const [code, setCode] = useState("");
  const [error, setError] = useState("");

  function load() {
    listDepartments()
      .then((response) => setDepartments(response.data))
      .catch((err) => setError(apiError(err, "Unable to load departments")));
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
      setError(apiError(err, "Unable to create department"));
    }
  }

  async function toggleActive(department) {
    await updateDepartment(department.id, { is_active: !department.is_active });
    load();
  }

  const activeCount = departments.filter((department) => department.is_active).length;

  return (
    <div className="stack">
      <PageHeader title="Departments" subtitle="Organization structure." />
      <section className="grid grid-3">
        <StatCard icon="building" label="Departments" value={departments.length} />
        <StatCard icon="activity" label="Active" value={activeCount} />
        <StatCard icon="pause" label="Inactive" value={departments.length - activeCount} />
      </section>
      <article className="card">
        <form className="filters" onSubmit={handleCreate}>
          <input className="input" placeholder="Name" value={name} onChange={(event) => setName(event.target.value)} required />
          <input className="input" placeholder="Code" value={code} onChange={(event) => setCode(event.target.value)} required />
          <button className="btn" type="submit">
            Create
          </button>
        </form>
        {error ? <div className="alert alert-error">{error}</div> : null}
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                <th>Code</th>
                <th>Name</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {departments.map((department) => (
                <tr key={department.id}>
                  <td>{department.code}</td>
                  <td>{department.name}</td>
                  <td>
                    <StatusBadge status={department.is_active ? "ACTIVE" : "OFFLINE"} />
                  </td>
                  <td>
                    <button className="btn btn-secondary" type="button" onClick={() => toggleActive(department)}>
                      {department.is_active ? "Deactivate" : "Activate"}
                    </button>
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
