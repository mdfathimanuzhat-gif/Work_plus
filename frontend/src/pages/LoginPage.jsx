import { useState } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";

import { Icon } from "../components/icons.jsx";
import { useAuth } from "../hooks/useAuth.jsx";
import { userMessage } from "../utils/format.js";

export default function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || "/dashboard";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  if (user) {
    return <Navigate to={from} replace />;
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(userMessage(err, "Sign-in failed. Check your email and password."));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="login-shell">
      <section className="login-brand">
        <div>
          <div className="brand-mark" style={{ width: 48, height: 48, fontSize: 18 }}>WP</div>
          <p className="login-kicker">WorkPulse</p>
          <h1>Work smarter. Stay productive.</h1>
          <p>
            Employee attendance and workforce visibility from the WorkPulse Agent —
            active time, idle intervals, and lock events in one place.
          </p>
        </div>
        <div className="orb" aria-hidden="true" />
      </section>
      <section className="login-panel">
        <form className="login-card" onSubmit={handleSubmit}>
          <p className="login-kicker dark">WorkPulse</p>
          <h2 style={{ margin: "0 0 0.25rem" }}>Welcome back</h2>
          <p className="muted">Sign in with your work email.</p>
          {error ? <div className="alert alert-error">{error}</div> : null}
          <label className="label">
            Email
            <input
              className="input"
              type="email"
              autoComplete="username"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </label>
          <label className="label">
            Password
            <div className="password-field">
              <input
                className="input"
                type={showPassword ? "text" : "password"}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
              <button type="button" onClick={() => setShowPassword((v) => !v)} aria-label={showPassword ? "Hide password" : "Show password"}>
                <Icon name={showPassword ? "eyeOff" : "eye"} size={16} />
              </button>
            </div>
          </label>
          <button className="btn" type="submit" disabled={submitting} style={{ width: "100%", justifyContent: "center", marginTop: 8 }}>
            {submitting ? "Signing in…" : "Login"}
          </button>
        </form>
      </section>
    </div>
  );
}
