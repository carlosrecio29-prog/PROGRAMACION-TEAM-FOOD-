export default function Badge({ children, tone = "" }) {
  return <span className={`v2-badge ${tone}`.trim()}>{children}</span>;
}
