import { Link } from "react-router-dom";
import Avatar from "./Avatar.jsx";
import { Icon } from "./icons.jsx";
import { displayName, primaryRole } from "../utils/format.js";

export default function TopHeader({ title, user, menuOpen, profileOpen, onMenu, onProfile, onLogout }) {
  return (
    <header className="topbar">
      <div className="topbar-left">
        <button type="button" className="menu-toggle" onClick={onMenu} aria-label="Open menu">
          <Icon name="menu" size={16} />
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
          <button type="button" className="user-chip" onClick={onProfile}>
            <Avatar first={user?.first_name} last={user?.last_name} />
            <span className="user-meta">
              <strong>{displayName(user)}</strong>
              <span>{primaryRole(user?.roles)}</span>
            </span>
          </button>
          <div className="dropdown-menu">
            <Link to="/profile">Profile</Link>
            <Link to="/settings">Settings</Link>
            <button type="button" onClick={onLogout}>
              Logout
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
