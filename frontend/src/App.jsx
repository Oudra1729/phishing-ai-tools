import { useCallback, useEffect, useState } from "react";
import { explain, fetchExamples, firstUrlFromText, predict } from "./api/client.js";
import { useHistory } from "./hooks/useHistory.js";
import ExampleUrls from "./components/ExampleUrls.jsx";
import ExplanationPanel from "./components/ExplanationPanel.jsx";
import HistoryList from "./components/HistoryList.jsx";
import { IconLink, IconMail } from "./components/Icons.jsx";
import ProgressRing from "./components/ProgressRing.jsx";
import RiskMeter from "./components/RiskMeter.jsx";
import LetterGlitch from "./components/LetterGlitch.jsx";
import SplashCursor from "./components/SplashCursor.jsx";
import "./App.css";

function StatusBadge({ dangerous }) {
  return (
    <span className={`status-badge ${dangerous ? "status-badge--danger" : "status-badge--safe"}`}>
      {dangerous ? "Dangerous" : "Safe"}
    </span>
  );
}

function ResultSection({ title, row, tonePrefix }) {
  if (!row) return null;
  const bad = row.label === 1;
  const proba = row.proba ?? row.proba_phishing ?? 0;
  const pct = proba * 100;

  return (
    <div className={`result-block ${bad ? "is-bad" : "is-good"} ${tonePrefix || ""}`}>
      <div className="result-block__row">
        <div className="result-block__main">
          <div className="section-label">{title}</div>
          <div className="result-block__title-row">
            <h3
              className={`result-verdict verdict-glow ${bad ? "verdict-glow--danger" : "verdict-glow--safe"}`}
            >
              {bad ? "Phishing risk" : "Likely legitimate"}
            </h3>
            <StatusBadge dangerous={bad} />
          </div>
          <div className="sub">
            Model <code>{row.model}</code>
            {row.adjustment && row.adjustment !== "none" ? (
              <>
                {" "}
                · <code>{row.adjustment}</code>
              </>
            ) : null}
          </div>
        </div>
        <ProgressRing
          value={pct}
          variant={bad ? "danger" : "safe"}
          label="Phishing"
        />
      </div>

      <div className="url-line">
        <span className="muted">URL</span> {row.url}
      </div>
      {row.domain && (
        <div className="url-line small muted">
          <span className="muted">Domain</span> {row.domain}
        </div>
      )}
      {row.proba_raw != null && (
        <div className="url-line small muted">
          Raw model score {(row.proba_raw * 100).toFixed(1)}%
        </div>
      )}
      <RiskMeter label="Model probability (bar)" valuePct={pct} tone="model" />
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
    <div className="app-shell">
      <div className="app-glitch-layer" aria-hidden>
        <div className="app-glitch-fill">
        <LetterGlitch
          glitchColors={["#2b4539", "#61dca3", "#61b3dc"]}
          glitchSpeed={50}
          centerVignette={false}
          outerVignette={false}
          smooth
          backgroundColor="#0a0a0c"
        />
        </div>
      </div>
      <div className="app-dim-overlay" aria-hidden />
      <div className="app-bg" aria-hidden />
      <div className="app-radial" aria-hidden />

      <header className="app-header">
        <div className="app-header__brand">
          <img className="app-header__logo" src="/logo.png" alt="" width={56} height={56} />
          <div className="app-header__titles">
            <span className="app-header__eyebrow">AI · Cybersecurity</span>
            <h1 className="app-header__title">Phishing URL Analyzer</h1>
            <p className="app-header__tagline">Détection &amp; génération de phishing par IA</p>
          </div>
        </div>
      </header>

      <div className="app-body">
        <main className="app-center">
          <section className="glass-card glass-card--tool">
            <div className="glass-card__head">
              <h2 className="glass-card__title">Analyze</h2>
              <p className="glass-card__hint">
                Main URL and email URLs are scored separately. Trusted domains reduce false positives.
              </p>
            </div>

            <label className="field-label" htmlFor="url-in">
              Main URL <span className="optional">(optional)</span>
            </label>
            <div className="input-shell">
              <span className="input-shell__icon" aria-hidden>
                <IconLink />
              </span>
              <input
                id="url-in"
                className="input-shell__control"
                type="url"
                placeholder="https://www.paypal.com/login"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                autoComplete="off"
              />
            </div>

            <label className="field-label mt" htmlFor="email-in">
              Email text <span className="optional">(optional)</span>
            </label>
            <div className="input-shell input-shell--area">
              <span className="input-shell__icon input-shell__icon--top" aria-hidden>
                <IconMail />
              </span>
              <textarea
                id="email-in"
                className="input-shell__control input-shell__control--area"
                rows={3}
                placeholder='e.g. "verify here https://secure-login-example.com"'
                value={emailText}
                onChange={(e) => setEmailText(e.target.value)}
              />
            </div>

            <button type="button" className="btn-analyze" disabled={loading} onClick={runAnalyze}>
              <span className="btn-analyze__shimmer" aria-hidden />
              <span className="btn-analyze__label">{loading ? "Analyzing…" : "Analyze"}</span>
            </button>

            {error && (
              <div className="alert" role="alert">
                {error}
              </div>
            )}
          </section>

          {(mainUrl || emailUrls.length > 0 || expl) && (
            <section className="glass-card glass-card--results">
              <h2 className="glass-card__title glass-card__title--sm">Results</h2>
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
                  <div className="structural-block">
                    <span className="structural-block__label">Structural risk (heuristic)</span>
                    <ProgressRing
                      value={expl.structural_risk_score}
                      size={84}
                      stroke={5}
                      variant="neutral"
                      label="Heuristic"
                    />
                  </div>
                  <ExplanationPanel data={expl} />
                </>
              )}
            </section>
          )}
        </main>

        <aside className="app-sidebar">
          <HistoryList items={history} onPick={onPickHistory} onClear={clear} />
          <ExampleUrls urls={examples} onUse={(u) => setUrl(u)} />
        </aside>
      </div>

      <footer className="app-footer">
        <span>POST /predict · POST /explain · GET /examples</span>
      </footer>

      <SplashCursor RAINBOW_MODE={false} COLOR="#22d3ee" DYE_RESOLUTION={900} />
    </div>
  );
}
