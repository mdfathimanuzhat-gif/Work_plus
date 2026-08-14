import { Outlet, Link } from "react-router-dom";

export default function AppLayout() {
  return (
    <div>
      <header className="app-header">
        <strong>WorkPulse</strong>
        <nav>
          <Link to="/">Home</Link>
          <Link to="/login">Sign in</Link>
        </nav>
      </header>
      <main className="app-main">
        <Outlet />
      </main>
    </div>
  );
}
