export default function StatusBadge({ status }) {
  const value = status || "OFFLINE";
  return (
    <span className={`badge status-${value}`}>
      <span className="dot" />
      {value}
    </span>
  );
}
