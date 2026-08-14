import { useEffect, useState } from "react";
import { getMyProfile, updateEmployee } from "../services/people.js";
import { useAuth } from "../hooks/useAuth.jsx";

export default function ProfilePage() {
  const { user } = useAuth();
  const [profile, setProfile] = useState(null);
  const [phone, setPhone] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    getMyProfile()
      .then((response) => {
        setProfile(response.data);
        setPhone(response.data.phone || "");
      })
      .catch((err) => setError(err.response?.data?.error?.message || "Unable to load profile"));
  }, []);

  async function handleSave(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    try {
      const response = await updateEmployee(user.employee_id, { phone });
      setProfile(response.data);
      setMessage("Profile updated");
    } catch (err) {
      setError(err.response?.data?.error?.message || "Unable to update profile");
    }
  }

  if (!profile) {
    return <p>{error || "Loading…"}</p>;
  }

  return (
    <section className="card">
      <h1>My Profile</h1>
      <dl className="details">
        <dt>Employee ID</dt>
        <dd>{profile.employee_code}</dd>
        <dt>Name</dt>
        <dd>
          {profile.first_name} {profile.last_name}
        </dd>
        <dt>Email</dt>
        <dd>{profile.email}</dd>
        <dt>Department</dt>
        <dd>{profile.department_name || "—"}</dd>
        <dt>Team</dt>
        <dd>{profile.team_name || "—"}</dd>
        <dt>Reporting Team Lead</dt>
        <dd>{profile.manager_name || "—"}</dd>
        <dt>Joining date</dt>
        <dd>{profile.joining_date || "—"}</dd>
        <dt>Employment status</dt>
        <dd>{profile.employment_status}</dd>
        <dt>Account status</dt>
        <dd>{profile.account_status}</dd>
      </dl>
      <form className="stack" onSubmit={handleSave}>
        <label>
          Phone
          <input value={phone} onChange={(event) => setPhone(event.target.value)} />
        </label>
        {message && <p className="success">{message}</p>}
        {error && <p className="error">{error}</p>}
        <button type="submit">Save personal details</button>
      </form>
    </section>
  );
}
