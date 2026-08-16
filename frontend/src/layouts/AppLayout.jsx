import { useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.jsx";
import Avatar from "../components/Avatar.jsx";
import { Icon } from "../components/icons.jsx";
import { displayName, primaryRole } from "../utils/format.js";

const TITLES = {
  "/dashboard": "Dashboard",
  "/attendance": "Attendance",
  "/timesheet": "Timesheet",
  "/history": "History",
  "/device": "Device",
  "/team": "Team",
  "/employees": "Employees",
  "/departments": "Departments",
  "/teams": "Teams",
  "/profile": "Profile",
  "/settings": "Settings",
};

export default function AppLayout() {
  const { user, logout, hasRole } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);
  const [profileOpen, setProfileOpen] = useState(false);

  useEffect(() => {
    setMenuOpen(false);
    setProfileOpen(false);
  }, [location.pathname]);

  async function handleLogout() {
    await logout();
    navigate("/login");
  }

  const title =
    Object.entries(TITLES).find(([path]) => location.pathname === path || location.pathname.startsWith(`${path}/`))?.[1] ||
    "WorkPulse";

  return (
    <div className="shell">
      {menuOpen ? <div className="backdrop" onClick={() => setMenuOpen(false)} /> : null}
      <aside className={`sidebar ${menuOpen ? "open" : ""}`}>
        <Link to="/dashboard" className="sidebar-brand">
          <span className="brand-mark">W</span>
          <span className="brand-text">
            <strong>WorkPulse</strong>
            <span>Workforce OS</span>
          </span>
        </Link>
        <nav className="sidebar-nav">
          <div className="nav-label">Work</div>
          <NavItem to="/dashboard" icon="dashboard" label="Dashboard" />
          <NavItem to="/attendance" icon="clock" label="Attendance" />
          <NavItem to="/timesheet" icon="file" label="Timesheet" />
          <NavItem to="/history" icon="history" label="History" />
          <NavItem to="/device" icon="device" label="Device" />
          {hasRole("TEAM_LEAD", "HR", "ADMIN") ? <NavItem to="/team" icon="users" label="Team" /> : null}
          {hasRole("HR", "ADMIN") ? (
            <>
              <div className="nav-label">Organization</div>
              <NavItem to="/employees" icon="users" label="Employees" />
              <NavItem to="/departments" icon="building" label="Departments" />
              <NavItem to="/teams" icon="users" label="Teams" />
            </>
          ) : null}
          <div className="nav-label">Account</div>
          <NavItem to="/profile" icon="user" label="Profile" />
          <NavItem to="/settings" icon="settings" label="Settings" />
        </nav>
        <div className="sidebar-footer">
          <button type="button" className="nav-item nav-logout" onClick={handleLogout}>
            <Icon name="logout" />
            Logout
          </button>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <div className="topbar-left">
            <button type="button" className="menu-toggle" onClick={() => setMenuOpen(true)} aria-label="Open menu">
              <Icon name="dashboard" size={16} />
            </button>
            <div>
              <div className="crumb">WorkPulse / {title}</div>
              <h1 className="page-title">{title}</h1>
            </div>
          </div>
          <div className="topbar-right">
            <button type="button" className="icon-btn" aria-label="Notifications">
              <Icon name="bell" />
            </button>
            <div className={`dropdown ${profileOpen ? "open" : ""}`}>
              <button type="button" className="user-chip" onClick={() => setProfileOpen((open) => !open)}>
                <Avatar first={user?.first_name} last={user?.last_name} />
                <span className="user-meta">
                  <strong>{displayName(user)}</strong>
                  <span>{primaryRole(user?.roles)}</span>
                </span>
              </button>
              <div className="dropdown-menu">
                <Link to="/profile">Profile</Link>
                <Link to="/settings">Settings</Link>
                <button type="button" onClick={handleLogout}>
                  Logout
                </button>
              </div>
            </div>
          </div>
        </header>
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

function NavItem({ to, icon, label }) {
  return (
    <NavLink to={to} className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
      <Icon name={icon} />
      {label}
    </NavLink>
  );
}
