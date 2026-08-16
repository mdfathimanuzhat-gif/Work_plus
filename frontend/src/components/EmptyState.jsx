export default function EmptyState({ title, message, body, icon }) {
  return (
    <div className="empty">
      {icon ? <div className="empty-icon">{icon}</div> : null}
      <strong>{title || "No activity recorded yet."}</strong>
      {message || body ? <p>{message || body}</p> : null}
    </div>
  );
}
