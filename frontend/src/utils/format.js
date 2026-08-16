export function formatDuration(seconds) {
  if (seconds == null || Number.isNaN(Number(seconds))) return "—";
  const total = Math.max(0, Math.floor(Number(seconds)));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  if (hours === 0 && minutes === 0) return "0m";
  if (hours === 0) return `${minutes}m`;
  return `${hours}h ${minutes}m`;
}

export function formatTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
}

export function formatDate(value) {
  if (!value) return "—";
  const date = value instanceof Date ? value : new Date(`${value}T00:00:00`);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric", year: "numeric" });
}

export function todayIso() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function greetingForHour(hour = new Date().getHours()) {
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

export function initials(first, last) {
  return `${(first || "").charAt(0)}${(last || "").charAt(0)}`.toUpperCase() || "WP";
}

export function displayName(person) {
  if (!person) return "—";
  return `${person.first_name || ""} ${person.last_name || ""}`.trim() || "—";
}

export function primaryRole(roles = []) {
  if (roles.includes("ADMIN")) return "Admin";
  if (roles.includes("HR")) return "HR";
  if (roles.includes("TEAM_LEAD")) return "Team Lead";
  if (roles.includes("EMPLOYEE")) return "Employee";
  return roles[0] || "—";
}

export function apiError(err, fallback) {
  return err?.response?.data?.error?.message || fallback;
}
