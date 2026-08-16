export default function EmptyState({ title, message }) {
  return (
    <div className="empty">
      <strong>{title}</strong>
      <p>{message}</p>
    </div>
  );
}
