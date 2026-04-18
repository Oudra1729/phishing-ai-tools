import "./ExampleUrls.css";

export default function ExampleUrls({ urls, onUse }) {
  if (!urls?.length) return null;

  return (
    <div className="examples">
      <h3>Example phishing-style URLs</h3>
      <p className="ex-sub">From the same generator as tests (seeded). Click to load.</p>
      <div className="ex-chips">
        {urls.map((u) => (
          <button key={u} type="button" className="chip" onClick={() => onUse(u)}>
            {u.length > 56 ? u.slice(0, 54) + "…" : u}
          </button>
        ))}
      </div>
    </div>
  );
}
