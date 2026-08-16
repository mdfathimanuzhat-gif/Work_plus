import StatusBadge from "./StatusBadge.jsx";
import { formatRelative, statusCopy } from "../utils/format.js";
import { splitDuration } from "../utils/format.js";
import { useLiveSeconds } from "../hooks/useLiveSeconds.js";

export default function LiveStatusCard({ live, day }) {
  const status = live?.state || "OFFLINE";
  const connected = Boolean(live && status !== "OFFLINE");
  const ticking = status === "ACTIVE";
  const seconds = useLiveSeconds(day?.total_active_seconds, live?.as_of, ticking);
  const parts = splitDuration(seconds);
  return (
    <section className="card hero-live">
      <div>
        <div className="muted">Current status</div>
        <div className={`hero-status status-${status}`} style={{ background: "transparent", padding: 0 }}>
          {status}
        </div>
        <p style={{ margin: "0 0 0.85rem" }}>{statusCopy(status)}</p>
        <div className="connect">{connected ? "WorkPulse Agent Connected" : "WorkPulse Agent Disconnected"}</div>
        <p className="muted" style={{ marginTop: "0.55rem" }}>
          Device: —
        </p>
      </div>
      <div className="clock-block">
        <div className="clock-hms">
          <div className="hm">
            {parts.hours}h {parts.minutes}m
          </div>
          <div className="sec">{parts.seconds}s</div>
        </div>
        <div className="muted" style={{ marginTop: "0.45rem" }}>
          Active today
        </div>
        <div className="muted">Updated {formatRelative(live?.as_of)}</div>
      </div>
    </section>
  );
}
