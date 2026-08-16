import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.jsx";
import { Icon } from "../components/icons.jsx";
import { apiError } from "../utils/format.js";

export default function LoginPage() {
  const { login, isAuthenticated, loading } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  if (!loading && isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      setError(apiError(err, "Unable to sign in"));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-shell">
      <section className="login-brand">
        <div>
          <div className="brand-mark">W</div>
          <h1>WorkPulse</h1>
          <p>Attendance and workforce visibility for modern teams — without surveillance noise.</p>
        </div>
        <p className="muted" style={{ color: "#9bb0c9" }}>
          Track sessions, idle time, and working hours from the desktop agent.
        </p>
      </section>
      <section className="login-panel">
        <div className="login-card">
          <h2 style={{ marginTop: 0 }}>Sign in</h2>
          <p className="muted">Use your WorkPulse account.</p>
          <form className="stack" onSubmit={handleSubmit} style={{ marginTop: "1.2rem" }}>
            <label className="label">
              Email
              <input className="input" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
            </label>
            <label className="label">
              Password
              <div className="password-field">
                <input
                  className="input"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                />
                <button type="button" onClick={() => setShowPassword((value) => !value)} aria-label={showPassword ? "Hide password" : "Show password"}>
                  <Icon name={showPassword ? "eyeOff" : "eye"} size={16} />
                </button>
              </div>
            </label>
            {error ? <div className="alert alert-error">{error}</div> : null}
            <button className="btn" type="submit" disabled={submitting}>
              {submitting ? "Signing in…" : "Sign in"}
            </button>
          </form>
        </div>
      </section>
    </div>
  );
}
