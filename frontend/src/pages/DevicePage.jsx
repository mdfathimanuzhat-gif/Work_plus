import { useEffect, useState } from "react";

import DeviceStatusCard from "../components/DeviceStatusCard.jsx";
import LoadingState from "../components/LoadingState.jsx";
import PageHeader from "../components/PageHeader.jsx";
import { getMyAttendanceLive } from "../services/attendance.js";
import { userMessage } from "../utils/format.js";

export default function DevicePage() {
  const [live, setLive] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const payload = await getMyAttendanceLive();
        if (!cancelled) setLive(payload);
      } catch (err) {
        if (!cancelled) setError(userMessage(err, "We couldn't load device status."));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="stack">
      <PageHeader
        title="Device"
        subtitle="WorkPulse Agent connection is inferred from live attendance. Hostname and pending event counts are not returned by this API."
      />
      {error ? <div className="alert alert-error">{error}</div> : null}
      {loading ? <LoadingState kind="card" /> : <DeviceStatusCard live={live} />}
    </div>
  );
}
