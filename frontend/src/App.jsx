import { useCallback, useEffect, useState } from "react";
import { explain, fetchExamples, firstUrlFromText, predict } from "./api/client.js";
import { useHistory } from "./hooks/useHistory.js";
import ExampleUrls from "./components/ExampleUrls.jsx";
import ExplanationPanel from "./components/ExplanationPanel.jsx";
import HistoryList from "./components/HistoryList.jsx";
import RiskMeter from "./components/RiskMeter.jsx";
import "./App.css";

function ResultSection({ title, row, tonePrefix }) {
  if (!row) return null;
  const bad = row.label === 1;
  const proba = row.proba ?? row.proba_phishing ?? 0;
  return (
    <div className={`result-block ${bad ? "is-bad" : "is-good"} ${tonePrefix || ""}`}>
      <div className="result-top">
        <div>
          <div className="section-label">{title}</div>
          <div className="verdict">{bad ? "Phishing" : "Safe"}</div>
          <div className="sub">
            Model: <code>{row.model}</code>
            {row.adjustment && row.adjustment !== "none" ? (
              <>
                {" "}
                · <code>{row.adjustment}</code>
              </>
            ) : null}
          </div>
        </div>
        <div className="prob-main">
          {(proba * 100).toFixed(1)}% <span>phishing prob. (adjusted)</span>
        </div>
      </div>
      <RiskMeter label="Phishing probability" valuePct={proba * 100} tone="model" />
      <div className="url-line">
        <span className="muted">URL:</span> {row.url}
      </div>
      {row.domain && (
        <div className="url-line small muted">
          <span className="muted">Registrable domain:</span> {row.domain}
        </div>
      )}
      {row.proba_raw != null && (
        <div className="url-line small muted">
          Raw model proba: {(row.proba_raw * 100).toFixed(1)}%
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [url, setUrl] = useState("");
  const [emailText, setEmailText] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [mainUrl, setMainUrl] = useState(null);
  const [emailUrls, setEmailUrls] = useState([]);
  const [expl, setExpl] = useState(null);
  const [examples, setExamples] = useState([]);
  const { items: history, push, clear } = useHistory();

  useEffect(() => {
    fetchExamples().then(({ data }) => {
      if (data?.urls) setExamples(data.urls);
    });
  }, []);

  const runAnalyze = useCallback(async () => {
    setError("");
    setMainUrl(null);
    setEmailUrls([]);
    setExpl(null);

    const u = url.trim();
    const em = emailText.trim();
    if (!u && !em) {
      setError("Enter a URL and/or paste email text.");
      return;
    }

    const payload = {};
    if (u) payload.url = u;
    if (em) payload.email_text = em;

    setLoading(true);
    try {
      const pr = await predict(payload);
      if (!pr.ok) {
        setError(pr.data?.error || `Predict failed (${pr.status})`);
        return;
      }
      const d = pr.data;
      const main = d.main_url || null;
      const emails = Array.isArray(d.email_urls) ? d.email_urls : [];

      if (!main && !emails.length) {
        setError("No results returned.");
        return;
      }

      setMainUrl(main);
      setEmailUrls(emails);

      const explainTarget = u || firstUrlFromText(em) || emails[0]?.url;
      if (explainTarget) {
        const ex = await explain(explainTarget);
        if (ex.ok) setExpl(ex.data);
      }

      const histRow = main || emails[0];
      if (histRow) {
        push({
          url: histRow.url,
          label: histRow.label,
          proba: histRow.proba ?? histRow.proba_phishing ?? 0,
        });
      }
    } catch (e) {
      setError("Network error — is the API running?");
    } finally {
      setLoading(false);
    }
  }, [url, emailText, push]);

  const onPickHistory = (u) => {
    setUrl(u);
    setEmailText("");
  };

  return (
    <div className="shell">
      <header className="hero">
        <div className="badge">AI · Security</div>
        <h1>Phishing URL Analyzer</h1>
        <p className="lead">
          Main URL and email URLs are scored separately. Trusted domains (e.g. paypal.com) reduce false
          positives from keywords like &quot;login&quot;.
        </p>
      </header>

      <main className="layout">
        <section className="card main-card">
          <label className="lbl">Main URL (optional)</label>
          <input
            className="inp"
            type="url"
            placeholder="https://www.paypal.com/login"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
          />

          <label className="lbl mt">Email text (optional)</label>
          <textarea
            className="tx"
            rows={3}
            placeholder='e.g. "verify here https://secure-login-google.com"'
            value={emailText}
            onChange={(e) => setEmailText(e.target.value)}
          />

          <button type="button" className="btn-primary" disabled={loading} onClick={runAnalyze}>
            {loading ? "Analyzing…" : "Analyze"}
          </button>

          {error && (
            <div className="alert" role="alert">
              {error}
            </div>
          )}

          <ResultSection title="Main URL" row={mainUrl} tonePrefix="main-sec" />

          {emailUrls.length > 0 && (
            <div className="email-section">
              <h3 className="section-label">URLs from email</h3>
              {emailUrls.map((row, i) => (
                <ResultSection key={row.url + i} title={`Email URL ${i + 1}`} row={row} tonePrefix="email-sec" />
              ))}
            </div>
          )}

          {expl && (
            <>
              <RiskMeter label="Structural risk (heuristic)" valuePct={expl.structural_risk_score} tone="structural" />
              <ExplanationPanel data={expl} />
            </>
          )}
        </section>

        <aside className="side">
          <HistoryList items={history} onPick={onPickHistory} onClear={clear} />
          <ExampleUrls urls={examples} onUse={(u) => setUrl(u)} />
        </aside>
      </main>

      <footer className="foot">
        <span>API: POST /predict (main_url + email_urls) · POST /explain · GET /examples</span>
      </footer>
    </div>
  );
}
