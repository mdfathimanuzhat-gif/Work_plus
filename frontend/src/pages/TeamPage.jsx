import { useEffect, useState } from "react";
import { listTeamMembers } from "../services/people.js";
import { useAuth } from "../hooks/useAuth.jsx";

export default function TeamPage() {
  const { user } = useAuth();
  const [members, setMembers] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!user?.team_id) {
      setError("You are not assigned to a team.");
      return;
    }
    listTeamMembers(user.team_id)
      .then((response) => setMembers(response.data))
      .catch((err) => setError(err.response?.data?.error?.message || "Unable to load team"));
  }, [user]);

  return (
    <section className="card">
      <h1>My Team</h1>
      {error && <p className="error">{error}</p>}
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Name</th>
            <th>Email</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {members.map((member) => (
            <tr key={member.id}>
              <td>{member.employee_code}</td>
              <td>
                {member.first_name} {member.last_name}
              </td>
              <td>{member.email}</td>
              <td>{member.employment_status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
