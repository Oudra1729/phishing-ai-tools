import "./HistoryList.css";

export default function HistoryList({ items, onPick, onClear }) {
  const hasItems = items?.length > 0;

  return (
    <div className="history-panel">
      <div className="history-panel__head">
        <h3 className="history-panel__title">Recent activity</h3>
        {hasItems && (
          <button type="button" className="history-panel__clear" onClick={onClear}>
            Clear
          </button>
        )}
      </div>

      {!hasItems ? (
        <div className="history-empty" aria-live="polite">
          <div className="history-empty__art" aria-hidden>
            <svg viewBox="0 0 120 100" fill="none" xmlns="http://www.w3.org/2000/svg">
              <rect x="10" y="20" width="100" height="60" rx="8" stroke="rgba(148,163,184,0.25)" strokeWidth="1.5" />
              <path d="M25 38h50M25 50h70M25 62h40" stroke="rgba(148,163,184,0.2)" strokeWidth="2" strokeLinecap="round" />
              <circle cx="88" cy="35" r="12" stroke="rgba(99,102,241,0.35)" strokeWidth="1.5" />
              <path d="M84 35h8M88 31v8" stroke="rgba(99,102,241,0.5)" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </div>
          <p className="history-empty__text">Your history will appear here after you analyze URLs.</p>
        </div>
      ) : (
        <ul className="history-list">
          {items.map((h) => {
            const dangerous = h.label === 1;
            return (
              <li key={h.at + h.url}>
                <button type="button" className="history-row" onClick={() => onPick(h.url)}>
                  <span className={`history-badge ${dangerous ? "history-badge--danger" : "history-badge--safe"}`}>
                    {dangerous ? "Dangerous" : "Safe"}
                  </span>
                  <span className="history-row__url">{truncate(h.url, 44)}</span>
                  <span className="history-row__pct">{((h.proba ?? 0) * 100).toFixed(0)}%</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function truncate(s, n) {
  if (!s) return "";
  return s.length <= n ? s : s.slice(0, n - 1) + "…";
}
