import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { analyzeClaim, fetchHealth } from "../api";

const initialForm = {
  title: "",
  content: "",
  source: "",
};

export default function AnalyzerPage() {
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(false);
  const [health, setHealth] = useState(null);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      const result = await analyzeClaim({
        title: form.title,
        content: form.content || null,
        source: form.source || null,
      });

      navigate(`/result/${result.id}`, {
        state: { result: { ...result, title: form.title, content: form.content, source: form.source } },
      });
    } catch (submissionError) {
      setError(submissionError.message);
    } finally {
      setLoading(false);
    }
  }

  async function loadHealth() {
    try {
      const status = await fetchHealth();
      setHealth(status);
    } catch (healthError) {
      setHealth({ status: "Unavailable", checks: { api: healthError.message } });
    }
  }

  return (
    <div className="page-stack">
      <section className="hero-card">
        <div>
          <p className="eyebrow">Analyzer</p>
          <h2>Evaluate a news claim for misinformation risk</h2>
          <p className="muted">
            Submit a title, optional body content, and optional source. The backend combines TF-IDF classical
            models, handcrafted feature engineering, and DistilBERT inference.
          </p>
        </div>

        <button className="secondary-button" type="button" onClick={loadHealth}>
          Check System Health
        </button>
      </section>

      {health && (
        <section className="panel">
          <div className="section-head">
            <div>
              <p className="eyebrow">Live Status</p>
              <h2>{health.status}</h2>
            </div>
          </div>
          <div className="signal-grid">
            {Object.entries(health.checks ?? {}).map(([key, value]) => (
              <article className="signal-card" key={key}>
                <span>{key}</span>
                <strong>{value}</strong>
              </article>
            ))}
          </div>
        </section>
      )}

      <section className="panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">Input</p>
            <h2>Claim Payload</h2>
          </div>
        </div>

        <form className="analysis-form" onSubmit={handleSubmit}>
          <label>
            <span>Title</span>
            <input
              required
              value={form.title}
              onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))}
              placeholder="Enter the headline or claim"
            />
          </label>

          <label>
            <span>Content</span>
            <textarea
              rows={8}
              value={form.content}
              onChange={(event) => setForm((current) => ({ ...current, content: event.target.value }))}
              placeholder="Optional supporting content"
            />
          </label>

          <label>
            <span>Source</span>
            <input
              value={form.source}
              onChange={(event) => setForm((current) => ({ ...current, source: event.target.value }))}
              placeholder="Optional publication or URL"
            />
          </label>

          {error ? <div className="error-box">{error}</div> : null}

          <div className="form-actions">
            <button className="primary-button" disabled={loading} type="submit">
              {loading ? "Analyzing..." : "Analyze Claim"}
            </button>
          </div>
        </form>
      </section>
    </div>
  );
}
