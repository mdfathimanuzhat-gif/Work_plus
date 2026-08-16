import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./hooks/useAuth.jsx";
import AppLayout from "./layouts/AppLayout.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import ProfilePage from "./pages/ProfilePage.jsx";
import TeamPage from "./pages/TeamPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import EmployeeListPage from "./pages/EmployeeListPage.jsx";
import EmployeeFormPage from "./pages/EmployeeFormPage.jsx";
import EmployeeDetailPage from "./pages/EmployeeDetailPage.jsx";
import DepartmentsPage from "./pages/DepartmentsPage.jsx";
import TeamsPage from "./pages/TeamsPage.jsx";

function HomePage() {
  return <Navigate to="/dashboard" replace />;
}
export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route path="/" element={<HomePage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route
              path="/team"
              element={
                <ProtectedRoute roles={["TEAM_LEAD", "HR", "ADMIN"]}>
                  <TeamPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/employees"
              element={
                <ProtectedRoute roles={["HR", "ADMIN"]}>
                  <EmployeeListPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/employees/new"
              element={
                <ProtectedRoute roles={["HR", "ADMIN"]}>
                  <EmployeeFormPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/employees/:employeeId"
              element={
                <ProtectedRoute roles={["HR", "ADMIN"]}>
                  <EmployeeDetailPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/employees/:employeeId/edit"
              element={
                <ProtectedRoute roles={["HR", "ADMIN"]}>
                  <EmployeeFormPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/departments"
              element={
                <ProtectedRoute roles={["HR", "ADMIN"]}>
                  <DepartmentsPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/teams"
              element={
                <ProtectedRoute roles={["HR", "ADMIN"]}>
                  <TeamsPage />
                </ProtectedRoute>
              }
            />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
