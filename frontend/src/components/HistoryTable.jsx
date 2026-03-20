import { Link } from "react-router-dom";
import RiskBadge from "./RiskBadge";

export default function HistoryTable({ rows }) {
  if (!rows.length) {
    return <div className="empty-state">No analysis history yet.</div>;
  }

  return (
    <div className="table-wrap">
      <table className="history-table">
        <thead>
          <tr>
            <th>Title</th>
            <th>Risk</th>
            <th>Confidence</th>
            <th>Created</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              <td>
                <strong>{row.title}</strong>
                <p>{row.explanation}</p>
              </td>
              <td>
                <RiskBadge level={row.riskLevel} />
              </td>
              <td>{Number(row.confidenceScore).toFixed(4)}</td>
              <td>{new Date(row.createdAt).toLocaleString()}</td>
              <td>
                <Link className="inline-link" to={`/result/${row.id}`}>
                  Open
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
