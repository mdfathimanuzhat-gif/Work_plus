import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.jsx";

export default function LoginPage() {
  const { login, isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  if (!loading && isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    try {
      const user = await login(email, password);
      if (user.roles?.includes("HR") || user.roles?.includes("ADMIN")) {
        navigate("/employees");
      } else if (user.roles?.includes("TEAM_LEAD")) {
        navigate("/team");
      } else {
        navigate("/profile");
      }
    } catch (err) {
      setError(err.response?.data?.error?.message || "Unable to sign in");
    }
  }

  return (
    <main className="app-main">
      <section className="card">
        <h1>Sign in</h1>
        <p className="placeholder-note">Development accounts use DEV_SEED_PASSWORD. Do not use production credentials.</p>
        <form className="stack" onSubmit={handleSubmit}>
          <label>
            Email
            <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </label>
          <label>
            Password
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required />
          </label>
          {error && <p className="error">{error}</p>}
          <button type="submit">Sign in</button>
        </form>
      </section>
    </main>
  );
}
