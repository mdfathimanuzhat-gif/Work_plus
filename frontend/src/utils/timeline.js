function sessionLabel(session, kind) {
  if (kind === "start") {
    if (session.status === "CONTINUED") return "Session continued";
    return "Session started";
  }
  return session.ended_reason ? `Session ended (${session.ended_reason})` : "Session ended";
}

export function timelineFromAttendanceDay(day) {
  if (!day) return [];
  const items = [];
  (day.sessions || []).forEach((session) => {
    items.push({
      id: `${session.id}-start`,
      label: sessionLabel(session, "start"),
      time: session.session_start,
      detail: session.status ? `Status ${session.status}` : null,
    });
    if (session.session_end) {
      items.push({
        id: `${session.id}-end`,
        label: sessionLabel(session, "end"),
        time: session.session_end,
      });
    }
  });
  (day.anomalies || []).forEach((anomaly, index) => {
    items.push({
      id: `anomaly-${index}-${anomaly.event_time}`,
      label: anomaly.event_type || anomaly.code,
      time: anomaly.event_time,
      detail: anomaly.message,
    });
  });
  return items.sort((a, b) => new Date(a.time) - new Date(b.time));
}
