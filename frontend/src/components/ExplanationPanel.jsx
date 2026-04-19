import "./ExplanationPanel.css";

export default function ExplanationPanel({ data }) {
  if (!data) return null;
  const ranked = data.features_ranked || [];
  const mitigating = data.mitigating_factors || [];

  return (
    <div className="explain-panel">
      <h3>Explanation (handcrafted features)</h3>
      <p className="explain-note">
        Approximate structural signals — the ML model also uses character TF-IDF, not listed here.
      </p>
      <div className="explain-grid">
        {ranked.map((f) => (
          <div key={f.id} className="explain-row">
            <div>
              <div className="explain-title">{f.title}</div>
              <div className="explain-desc">{f.description}</div>
            </div>
            <div className="explain-meta">
              <span className="explain-chip explain-chip--risk">
                +{(f.contribution_pct ?? 0).toFixed(1)}%
              </span>
              <span className="val">value: {formatVal(f.value)}</span>
            </div>
          </div>
        ))}
      </div>
      {mitigating.length > 0 && (
        <div className="mitigating">
          <h4>Mitigating factors</h4>
          <ul>
            {mitigating.map((f) => (
              <li key={f.id}>
                <strong>{f.title}</strong> — score {f.signed_score} (value {formatVal(f.value)})
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function formatVal(v) {
  if (typeof v !== "number") return String(v);
  if (Number.isInteger(v)) return String(v);
  return v.toFixed(3);
}
