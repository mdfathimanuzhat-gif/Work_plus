const LABELS = {
  LOGIN: "Windows Login",
  WINDOWS_LOGIN: "Windows Login",
  LOGOUT: "Windows Logout",
  WINDOWS_LOGOUT: "Windows Logout",
  LOCK: "System Lock",
  SYSTEM_LOCK: "System Lock",
  UNLOCK: "System Unlock",
  SYSTEM_UNLOCK: "System Unlock",
  IDLE_START: "Idle Start",
  IDLE_END: "Idle End",
  SHUTDOWN: "Shutdown",
  SYSTEM_SHUTDOWN: "Shutdown",
  RESTART: "Restart",
  SYSTEM_RESTART: "Restart",
  SLEEP: "Sleep",
  SYSTEM_SLEEP: "Sleep",
  WAKE: "Wake",
  SYSTEM_WAKE: "Wake",
};

export function eventLabel(type) {
  if (!type) return "Activity";
  return LABELS[type] || String(type).replaceAll("_", " ");
}

export function eventIcon(type) {
  const key = String(type || "").toUpperCase();
  if (key.includes("LOCK") && !key.includes("UNLOCK")) return "lock";
  if (key.includes("UNLOCK")) return "unlock";
  if (key.includes("IDLE_START") || key === "IDLE") return "pause";
  if (key.includes("IDLE_END") || key.includes("ACTIVE")) return "activity";
  if (key.includes("LOGOUT") || key.includes("SHUTDOWN")) return "logout";
  if (key.includes("LOGIN") || key.includes("WAKE")) return "login";
  if (key.includes("SLEEP")) return "moon";
  if (key.includes("RESTART")) return "history";
  return "clock";
}

export function timelineFromAttendanceDay(day) {
  if (!day) return [];
  const items = [];
  (day.sessions || []).forEach((session, index) => {
    const startType = index === 0 && day.first_login_time ? "WINDOWS_LOGIN" : "SESSION_START";
    items.push({
      id: `${session.id}-start`,
      type: startType,
      label: index === 0 && day.first_login_time ? "Windows Login" : "Session started",
      time: session.session_start,
      detail: session.status ? `Session ${session.status}` : null,
    });
    if (session.session_end) {
      const endType = session.ended_reason?.toUpperCase?.().includes("LOGOUT") ? "WINDOWS_LOGOUT" : "SESSION_END";
      items.push({
        id: `${session.id}-end`,
        type: endType,
        label: session.ended_reason ? eventLabel(session.ended_reason) : "Session ended",
        time: session.session_end,
      });
    }
  });
  (day.anomalies || []).forEach((anomaly, index) => {
    items.push({
      id: `anomaly-${index}-${anomaly.event_time}`,
      type: anomaly.event_type || anomaly.code,
      label: eventLabel(anomaly.event_type || anomaly.code),
      time: anomaly.event_time,
      detail: anomaly.message,
    });
  });
  return items.sort((a, b) => new Date(a.time) - new Date(b.time));
}

export function buildTimeline(sessions, anomalies) {
  return timelineFromAttendanceDay({ sessions, anomalies });
}
