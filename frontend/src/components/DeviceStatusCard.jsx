import StatusBadge from "./StatusBadge.jsx";
import { formatRelative } from "../utils/format.js";

export default function DeviceStatusCard({
  live,
  connected,
  deviceName,
  operatingSystem,
  lastSync,
  pendingEvents,
}) {
  const isConnected = connected ?? Boolean(live && live.state && live.state !== "OFFLINE");
  const syncLabel = lastSync ?? (live?.as_of ? formatRelative(live.as_of) : "—");

  return (
    <article className="card">
      <div className="row-between">
        <h2 className="card-title" style={{ margin: 0 }}>
          WorkPulse Agent
        </h2>
        <StatusBadge status={isConnected ? "ACTIVE" : "OFFLINE"} />
      </div>
      <p className={`connect ${isConnected ? "" : "connect-off"}`} style={{ marginTop: "0.7rem" }}>
        <span className="dot" /> {isConnected ? "Connected" : "Disconnected"}
      </p>
      <dl className="details" style={{ marginTop: "0.9rem" }}>
        <dt>Device</dt>
        <dd>{deviceName || "—"}</dd>
        <dt>Operating system</dt>
        <dd>{operatingSystem || "—"}</dd>
        <dt>Last sync</dt>
        <dd>{syncLabel}</dd>
        <dt>Pending events</dt>
        <dd>{pendingEvents ?? "—"}</dd>
      </dl>
    </article>
  );
}
