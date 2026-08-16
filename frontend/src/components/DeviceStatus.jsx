import StatusBadge from "./StatusBadge.jsx";

export default function DeviceStatus({ connected, deviceName, operatingSystem, lastSync, pendingEvents }) {
  return (
    <article className="card">
      <div className="row-between">
        <h2 className="card-title">WorkPulse Agent</h2>
        <StatusBadge status={connected ? "ACTIVE" : "OFFLINE"} />
      </div>
      <dl className="details">
        <dt>Connection</dt>
        <dd>{connected ? "Connected" : "Disconnected"}</dd>
        <dt>Device name</dt>
        <dd>{deviceName || "—"}</dd>
        <dt>Operating system</dt>
        <dd>{operatingSystem || "—"}</dd>
        <dt>Last synchronization</dt>
        <dd>{lastSync || "—"}</dd>
        <dt>Pending events</dt>
        <dd>{pendingEvents ?? "—"}</dd>
      </dl>
    </article>
  );
}
