import { Icon } from "./icons.jsx";
import { formatTime } from "../utils/format.js";
import { eventIcon } from "../utils/timeline.js";

export default function ActivityTimeline({ items }) {
  const list = Array.isArray(items) ? items : [];
  if (!list.length) return null;
  return (
    <ol className="timeline">
      {list.map((item, index) => (
        <li key={item.id != null ? `${item.id}-${index}` : index}>
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
