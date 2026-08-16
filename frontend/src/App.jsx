import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./hooks/useAuth.jsx";
import AppLayout from "./layouts/AppLayout.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import LoginPage from "./pages/LoginPage.jsx";
import DashboardPage from "./pages/DashboardPage.jsx";
import AttendancePage from "./pages/AttendancePage.jsx";
import TimesheetPage from "./pages/TimesheetPage.jsx";
import HistoryPage from "./pages/HistoryPage.jsx";
import DevicePage from "./pages/DevicePage.jsx";
import ProfilePage from "./pages/ProfilePage.jsx";
import SettingsPage from "./pages/SettingsPage.jsx";
import TeamPage from "./pages/TeamPage.jsx";
import EmployeeListPage from "./pages/EmployeeListPage.jsx";
import EmployeeFormPage from "./pages/EmployeeFormPage.jsx";
import EmployeeDetailPage from "./pages/EmployeeDetailPage.jsx";
import DepartmentsPage from "./pages/DepartmentsPage.jsx";
import TeamsPage from "./pages/TeamsPage.jsx";
import ApprovalsPage from "./pages/ApprovalsPage.jsx";

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
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/attendance" element={<AttendancePage />} />
            <Route path="/timesheet" element={<TimesheetPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/device" element={<DevicePage />} />
            <Route path="/profile" element={<ProfilePage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route
              path="/team"
              element={
                <ProtectedRoute roles={["TEAM_LEAD", "HR", "ADMIN"]}>
                  <TeamPage />
                </ProtectedRoute>
              }
            />
            <Route
              path="/approvals"
              element={
                <ProtectedRoute roles={["TEAM_LEAD", "HR", "ADMIN"]}>
                  <ApprovalsPage />
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
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
