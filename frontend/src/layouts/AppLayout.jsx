import { Link, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.jsx";

export default function AppLayout() {
  const { user, logout, hasRole } = useAuth();
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  return (
    <div>
      <header className="app-header">
        <strong>WorkPulse</strong>
        <nav>
          {hasRole("EMPLOYEE", "TEAM_LEAD", "HR", "ADMIN") && <Link to="/profile">My Profile</Link>}
          {hasRole("TEAM_LEAD") && <Link to="/team">My Team</Link>}
          {hasRole("HR", "ADMIN") && <Link to="/employees">Employees</Link>}
          {hasRole("HR", "ADMIN") && <Link to="/departments">Departments</Link>}
          {hasRole("HR", "ADMIN") && <Link to="/teams">Teams</Link>}
          <button type="button" className="link-button" onClick={handleLogout}>
            Sign out {user?.first_name}
          </button>
        </nav>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
