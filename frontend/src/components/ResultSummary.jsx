import RiskBadge from "./RiskBadge";

export default function ResultSummary({ result }) {
  return (
    <section className="hero-card">
      <div>
        <p className="eyebrow">Assessment Output</p>
        <h2>{result.title ?? "Submitted Claim"}</h2>
        <p className="muted">
          {result.content?.slice(0, 220) || "Title-only assessment"}{result.content?.length > 220 ? "..." : ""}
        </p>
      </div>

      <div className="hero-metrics">
        <div className="metric-block">
          <span>Risk Level</span>
          <RiskBadge level={result.riskLevel} />
        </div>
        <div className="metric-block">
          <span>Confidence Score</span>
          <strong>{Number(result.confidenceScore).toFixed(4)}</strong>
        </div>
      </div>

      <div className="summary-footer">
        <span>Created</span>
        <strong>{new Date(result.createdAt).toLocaleString()}</strong>
      </div>
    </section>
  );
}
