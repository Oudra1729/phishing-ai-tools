import "./HistoryList.css";

export default function HistoryList({ items, onPick, onClear }) {
  if (!items.length) return null;

  return (
    <div className="history">
      <div className="history-head">
        <h3>Recent (last 5)</h3>
        <button type="button" className="link-btn" onClick={onClear}>
          Clear
        </button>
      </div>
      <ul>
        {items.map((h) => (
          <li key={h.at + h.url}>
            <button type="button" className="history-item" onClick={() => onPick(h.url)}>
              <span className={`dot ${h.label === 1 ? "bad" : "good"}`} />
              <span className="u">{truncate(h.url, 48)}</span>
              <span className="p">{((h.proba ?? 0) * 100).toFixed(0)}%</span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

function truncate(s, n) {
  if (!s) return "";
  return s.length <= n ? s : s.slice(0, n - 1) + "…";
}
