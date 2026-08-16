import { useEffect, useState } from "react";
import DeviceStatus from "../components/DeviceStatus.jsx";
import PageHeader from "../components/PageHeader.jsx";
import StatusBadge from "../components/StatusBadge.jsx";
import { getMyLiveAttendance } from "../services/attendance.js";
import { formatTime } from "../utils/format.js";

export default function DevicePage() {
  const [live, setLive] = useState(null);

  useEffect(() => {
    getMyLiveAttendance()
      .then((response) => setLive(response.data))
      .catch(() => setLive(null));
  }, []);

  const connected = Boolean(live && live.state && live.state !== "OFFLINE");

  return (
    <div className="stack">
      <PageHeader title="Device" subtitle="Desktop agent connection inferred from live attendance state." />
      <DeviceStatus
        connected={connected}
        deviceName={null}
        operatingSystem={null}
        lastSync={formatTime(live?.as_of)}
        pendingEvents={null}
      />
      <article className="card">
        <h2 className="card-title">Live state</h2>
        <div className="row">
          <StatusBadge status={live?.state || "OFFLINE"} />
          <span className="muted">Timezone {live?.timezone || "—"}</span>
        </div>
        <p className="muted" style={{ marginTop: "0.8rem" }}>
          Device name, operating system, and pending event counts are not exposed by the current attendance APIs.
        </p>
      </article>
    </div>
  );
}
