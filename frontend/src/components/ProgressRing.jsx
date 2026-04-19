import "./ProgressRing.css";

/**
 * Circular progress 0–100. `variant` colors the arc (safe = green-ish, danger = red-ish).
 */
export default function ProgressRing({
  value,
  size = 92,
  stroke = 6,
  variant = "danger",
  label = "Risk",
}) {
  const v = Math.max(0, Math.min(100, Number(value) || 0));
  const r = (size - stroke) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const c = 2 * Math.PI * r;
  const offset = c - (v / 100) * c;

  return (
    <div className={`progress-ring ${variant}`} style={{ width: size, height: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden>
        <circle className="progress-ring__track" cx={cx} cy={cy} r={r} strokeWidth={stroke} fill="none" />
        <circle
          className="progress-ring__arc"
          cx={cx}
          cy={cy}
          r={r}
          strokeWidth={stroke}
          strokeDasharray={c}
          strokeDashoffset={offset}
          fill="none"
          transform={`rotate(-90 ${cx} ${cy})`}
        />
      </svg>
      <div className="progress-ring__center">
        <span className="progress-ring__pct">{v.toFixed(0)}%</span>
        <span className="progress-ring__lbl">{label}</span>
      </div>
    </div>
  );
}
