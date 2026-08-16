export default function Avatar({ first, last, name, size = "sm" }) {
  let given = first;
  let family = last;
  if ((!given && !family) && name) {
    const parts = String(name).trim().split(/\s+/);
    given = parts[0];
    family = parts.slice(1).join(" ");
  }
  const letters = `${(given || "").charAt(0)}${(family || "").charAt(0)}`.toUpperCase() || "WP";
  return <span className={`avatar ${size === "lg" || size > 40 ? "lg" : ""}`}>{letters}</span>;
}
