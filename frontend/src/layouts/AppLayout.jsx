import { useEffect, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import Sidebar from "../components/Sidebar.jsx";
import TopHeader from "../components/TopHeader.jsx";
import { useAuth } from "../hooks/useAuth.jsx";

const TITLES = {
  "/dashboard": "Dashboard",
  "/attendance": "My Attendance",
  "/timesheet": "Timesheet",
  "/history": "Activity History",
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
      <Sidebar user={user} hasRole={hasRole} open={menuOpen} onLogout={handleLogout} />
      <div className="workspace">
        <TopHeader
          title={title}
          user={user}
          profileOpen={profileOpen}
          onMenu={() => setMenuOpen(true)}
          onProfile={() => setProfileOpen((open) => !open)}
          onLogout={handleLogout}
        />
        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
