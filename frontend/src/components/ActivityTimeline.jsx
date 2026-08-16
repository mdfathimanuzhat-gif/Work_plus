import { formatTime } from "../utils/format.js";

export default function ActivityTimeline({ items }) {
  if (!items?.length) return null;
  return (
    <ol className="timeline">
      {items.map((item) => (
        <li key={item.id}>
          <span className="tl-dot" />
          <div>
            <div className="tl-title">{item.label}</div>
            {item.detail ? <div className="muted">{item.detail}</div> : null}
          </div>
          <div className="muted">{formatTime(item.time)}</div>
        </li>
      ))}
    </ol>
  );
}
