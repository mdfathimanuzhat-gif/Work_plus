export function formatDuration(seconds) {
  if (seconds == null || Number.isNaN(Number(seconds))) return "—";
  const total = Math.max(0, Math.floor(Number(seconds)));
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor((total % 3600) / 60);
  if (hours === 0 && minutes === 0) return "0m";
  if (hours === 0) return `${minutes}m`;
  return `${String(hours).padStart(2, "0")}h ${String(minutes).padStart(2, "0")}m`;
}

export function splitDuration(seconds) {
  const total = Math.max(0, Math.floor(Number(seconds) || 0));
  return {
    hours: String(Math.floor(total / 3600)).padStart(2, "0"),
    minutes: String(Math.floor((total % 3600) / 60)).padStart(2, "0"),
    seconds: String(total % 60).padStart(2, "0"),
  };
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

export function formatRelative(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  const delta = Date.now() - date.getTime();
  if (delta < 45_000) return "Just now";
  if (delta < 3600_000) return `${Math.floor(delta / 60000)} min ago`;
  return formatTime(value);
}

export function todayIso() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
}

export const localDateKey = todayIso;

export function formatClock(value = new Date()) {
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleDateString(undefined, {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

export function display(value) {
  if (value == null || value === "") return "—";
  return value;
}

export function greetingForHour(hour = new Date().getHours()) {
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

export function displayName(person) {
  if (!person) return "—";
  return `${person.first_name || ""} ${person.last_name || ""}`.trim() || "—";
}

export function firstName(person) {
  return person?.first_name || displayName(person);
}

export function primaryRole(roles = []) {
  if (roles.includes("ADMIN")) return "Admin";
  if (roles.includes("HR")) return "HR";
  if (roles.includes("TEAM_LEAD")) return "Team Lead";
  if (roles.includes("EMPLOYEE")) return "Employee";
  return roles[0] || "—";
}

export function userMessage(err, fallback) {
  const status = err?.response?.status;
  if (!err?.response) return "Unable to reach WorkPulse. Check your connection.";
  if (status === 401) return "Your session expired. Please sign in again.";
  if (status === 403) return "You don’t have access to this page.";
  if (status >= 500) return "Something went wrong. Try again shortly.";
  return err?.response?.data?.error?.message || fallback;
}

export function apiError(err, fallback) {
  return userMessage(err, fallback);
}

export function statusCopy(state) {
  switch (state) {
    case "ACTIVE":
      return "You're currently working";
    case "IDLE":
      return "You're currently idle";
    case "LOCKED":
      return "Your workstation is locked";
    case "SLEEPING":
      return "Your device is sleeping";
    default:
      return "You're currently offline";
  }
}
