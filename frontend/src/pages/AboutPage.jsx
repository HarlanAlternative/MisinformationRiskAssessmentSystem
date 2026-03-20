export default function AboutPage() {
  return (
    <div className="page-stack">
      <section className="hero-card">
        <div>
          <p className="eyebrow">About</p>
          <h2>Production-oriented misinformation risk platform</h2>
          <p className="muted">
            The system is designed as a portfolio-grade ML engineering project with a .NET 8 API, Azure SQL
            persistence, a React frontend, and a FastAPI DistilBERT inference service.
          </p>
        </div>
      </section>

      <section className="panel">
        <div className="section-head">
          <div>
            <p className="eyebrow">System Design</p>
            <h2>Architecture</h2>
          </div>
        </div>

        <div className="signal-grid">
          <article className="signal-card">
            <span>Backend</span>
            <strong>ASP.NET Core Web API + EF Core + Azure SQL</strong>
          </article>
          <article className="signal-card">
            <span>Classical Models</span>
            <strong>TF-IDF, n-grams, Logistic Regression, Random Forest</strong>
          </article>
          <article className="signal-card">
            <span>Transformer</span>
            <strong>FastAPI + HuggingFace DistilBERT</strong>
          </article>
          <article className="signal-card">
            <span>Explainability</span>
            <strong>Rule signals, lexical cues, transformer salient tokens</strong>
          </article>
        </div>
      </section>
    </div>
  );
}
