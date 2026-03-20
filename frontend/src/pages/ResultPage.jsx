import { useEffect, useState } from "react";
import { useLocation, useParams } from "react-router-dom";
import { fetchResult } from "../api";
import ResultSummary from "../components/ResultSummary";
import SignalPanel from "../components/SignalPanel";

export default function ResultPage() {
  const { id } = useParams();
  const location = useLocation();
  const [result, setResult] = useState(location.state?.result ?? null);
  const [loading, setLoading] = useState(!location.state?.result);
  const [error, setError] = useState("");

  useEffect(() => {
    if (location.state?.result) {
      return;
    }

    let active = true;

    async function load() {
      setLoading(true);
      try {
        const response = await fetchResult(id);
        if (active) {
          setResult(response);
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
  }, [id, location.state]);

  if (loading) {
    return <div className="empty-state">Loading analysis result...</div>;
  }

  if (error) {
    return <div className="error-box">{error}</div>;
  }

  if (!result) {
    return <div className="empty-state">Result not found.</div>;
  }

  return (
    <div className="page-stack">
      <ResultSummary result={result} />

      <section className="panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">Narrative Explanation</p>
            <h2>Why this score was assigned</h2>
          </div>
        </div>
        <p className="explanation-copy">{result.explanation}</p>
      </section>

      <SignalPanel featureSignals={result.featureSignals} />
    </div>
  );
}
