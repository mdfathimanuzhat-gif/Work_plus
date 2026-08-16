export default function Avatar({ first, last, size = "sm" }) {
  const letters = `${(first || "").charAt(0)}${(last || "").charAt(0)}`.toUpperCase() || "WP";
  return <span className={`avatar ${size === "lg" ? "lg" : ""}`}>{letters}</span>;
}
