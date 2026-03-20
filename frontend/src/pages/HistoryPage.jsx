import { useEffect, useState } from "react";
import { fetchHistory } from "../api";
import HistoryTable from "../components/HistoryTable";

export default function HistoryPage() {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const history = await fetchHistory();
        if (active) {
          setRows(history);
        }
      } catch (requestError) {
        if (active) {
          setError(requestError.message);
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    load();
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="page-stack">
      <section className="hero-card">
        <div>
          <p className="eyebrow">History</p>
          <h2>Recent analysis results</h2>
          <p className="muted">Persisted through Entity Framework Core and Azure SQL-compatible storage.</p>
        </div>
      </section>

      {loading ? <div className="empty-state">Loading history...</div> : null}
      {error ? <div className="error-box">{error}</div> : null}
      {!loading && !error ? <HistoryTable rows={rows} /> : null}
    </div>
  );
}
