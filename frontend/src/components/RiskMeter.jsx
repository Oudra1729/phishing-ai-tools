import "./RiskMeter.css";

export default function RiskMeter({ label, valuePct, tone = "model" }) {
  const v = Math.max(0, Math.min(100, Number(valuePct) || 0));
  const barClass =
    tone === "structural"
      ? v > 60
        ? "fill warn"
        : "fill ok"
      : v > 55
        ? "fill bad"
        : "fill good";

  return (
    <div className="risk-meter">
      <div className="risk-meter-head">
        <span>{label}</span>
        <strong>{v.toFixed(1)}%</strong>
      </div>
      <div className="risk-meter-track" role="progressbar" aria-valuenow={v} aria-valuemin={0} aria-valuemax={100}>
        <div className={`risk-meter-fill ${barClass}`} style={{ width: `${v}%` }} />
      </div>
    </div>
  );
}
