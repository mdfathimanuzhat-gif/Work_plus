import { Link, NavLink } from "react-router-dom";
import Avatar from "./Avatar.jsx";
import { Icon } from "./icons.jsx";
import { displayName, primaryRole } from "../utils/format.js";

export default function Sidebar({ user, hasRole, open, onLogout }) {
  return (
    <aside className={`sidebar ${open ? "open" : ""}`}>
      <Link to="/dashboard" className="sidebar-brand">
        <span className="brand-mark">W</span>
        <span className="brand-text">
          <strong>WorkPulse</strong>
          <span>Workforce OS</span>
        </span>
      </Link>
      <nav className="sidebar-nav">
        <div className="nav-label">Workspace</div>
        <Item to="/dashboard" icon="dashboard" label="Dashboard" />
        <Item to="/attendance" icon="clock" label="Attendance" />
        <Item to="/timesheet" icon="file" label="Timesheet" />
        <Item to="/history" icon="history" label="Activity History" />
        {hasRole("TEAM_LEAD", "HR", "ADMIN") || hasRole("HR", "ADMIN") ? <div className="nav-label">Management</div> : null}
        {hasRole("TEAM_LEAD", "HR", "ADMIN") ? <Item to="/team" icon="users" label="Team" /> : null}
        {hasRole("HR", "ADMIN") ? (
          <>
            <Item to="/employees" icon="users" label="Employees" />
            <Item to="/departments" icon="building" label="Departments" />
            <Item to="/teams" icon="users" label="Teams" />
          </>
        ) : null}
        <div className="nav-label">System</div>
        <Item to="/device" icon="device" label="Device" />
        <Item to="/profile" icon="user" label="Profile" />
        <Item to="/settings" icon="settings" label="Settings" />
      </nav>
      <div className="sidebar-user">
        <Avatar first={user?.first_name} last={user?.last_name} />
        <div>
          <strong>{displayName(user)}</strong>
          <span>{primaryRole(user?.roles)}</span>
        </div>
      </div>
      <button type="button" className="nav-item nav-logout" onClick={onLogout}>
        <Icon name="logout" />
        Logout
      </button>
    </aside>
  );
}

function Item({ to, icon, label }) {
  return (
    <NavLink to={to} className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}>
      <Icon name={icon} />
      {label}
    </NavLink>
  );
}
