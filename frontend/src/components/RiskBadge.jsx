export default function RiskBadge({ level }) {
  const normalized = (level ?? "Low").toLowerCase();
  return <span className={`risk-badge ${normalized}`}>{level}</span>;
}
