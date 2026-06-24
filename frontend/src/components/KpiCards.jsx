import "./KpiCards.css";

function efficiencyStatus(score) {
  if (score >= 80) return "good";
  if (score >= 60) return "warn";
  return "bad";
}

export default function KpiCards({ summary }) {
  if (!summary) return null;

  const status = efficiencyStatus(summary.efficiency_score);

  const cards = [
    { label: "Total Hours", value: summary.total_hours, unit: "h" },
    { label: "Productive Hours", value: summary.productive_hours, unit: "h", accent: "good" },
    { label: "Downtime Hours", value: summary.downtime_hours, unit: "h", accent: "bad" },
    { label: "Records", value: summary.record_count, unit: "" },
  ];

  return (
    <div className="kpi-row">
      <div className="kpi-card kpi-card--hero">
        <span className="kpi-card__label">Operational Efficiency Score</span>
        <div className="kpi-card__hero-value-row">
          <span className={`kpi-card__hero-value status-${status}`}>{summary.efficiency_score}</span>
          <span className="kpi-card__hero-unit">%</span>
        </div>
        <div className="kpi-card__gauge">
          <div
            className={`kpi-card__gauge-fill status-${status}`}
            style={{ width: `${Math.min(summary.efficiency_score, 100)}%` }}
          />
        </div>
        <span className="kpi-card__sub">Productive ÷ Total hours</span>
      </div>

      {cards.map((card) => (
        <div className="kpi-card" key={card.label}>
          <span className="kpi-card__label">{card.label}</span>
          <div className="kpi-card__value-row">
            <span className={`kpi-card__value mono${card.accent ? ` status-${card.accent}` : ""}`}>
              {card.value}
            </span>
            {card.unit && <span className="kpi-card__unit">{card.unit}</span>}
          </div>
        </div>
      ))}
    </div>
  );
}
