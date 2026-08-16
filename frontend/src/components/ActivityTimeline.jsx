import { Icon } from "./icons.jsx";
import { formatTime } from "../utils/format.js";
import { eventIcon } from "../utils/timeline.js";

export default function ActivityTimeline({ items }) {
  if (!items?.length) return null;
  return (
    <ol className="timeline">
      {items.map((item) => (
        <li key={item.id}>
          <span className="tl-icon">
            <Icon name={eventIcon(item.type)} size={14} />
          </span>
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
