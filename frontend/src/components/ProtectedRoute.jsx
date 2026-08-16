import { Navigate } from "react-router-dom";
import { useAuth } from "../hooks/useAuth.jsx";
import LoadingState from "./LoadingState.jsx";

export default function ProtectedRoute({ children, roles }) {
  const { isAuthenticated, loading, hasRole } = useAuth();
  if (loading) {
    return <LoadingState label="Checking your session…" />;
  }
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }
  if (roles?.length && !hasRole(...roles)) {
    return <Navigate to="/dashboard" replace />;
  }
  return children;
}
