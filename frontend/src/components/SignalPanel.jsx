function formatValue(key, value) {
  if (typeof value === "number") {
    return value > 0 && value < 1 ? value.toFixed(4) : value;
  }

  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "None";
  }

  if (typeof value === "object" && value !== null) {
    return Object.entries(value)
      .map(([entryKey, entryValue]) => `${entryKey}: ${Number(entryValue).toFixed(4)}`)
      .join(" | ");
  }

  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }

  return value ?? "N/A";
}

const labels = {
  textLength: "Text Length",
  wordCount: "Word Count",
  punctuationCount: "Punctuation Count",
  emotionalWordRatio: "Emotional Word Ratio",
  uppercaseRatio: "Uppercase Ratio",
  exclamationCount: "Exclamation Count",
  exaggerationCount: "Exaggeration Count",
  hasSource: "Source Provided",
  topKeywords: "Top Keywords",
  transformerTokens: "Transformer Tokens",
  modelScores: "Model Scores",
};

export default function SignalPanel({ featureSignals }) {
  if (!featureSignals) {
    return null;
  }

  return (
    <section className="panel">
      <div className="section-head">
        <div>
          <p className="eyebrow">Explainability</p>
          <h2>Feature Signals</h2>
        </div>
      </div>

      <div className="signal-grid">
        {Object.entries(featureSignals).map(([key, value]) => (
          <article className="signal-card" key={key}>
            <span>{labels[key] ?? key}</span>
            <strong>{formatValue(key, value)}</strong>
          </article>
        ))}
      </div>
    </section>
  );
}
