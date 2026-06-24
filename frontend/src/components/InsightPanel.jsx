import "./InsightPanel.css";

const SEVERITY_CLASS = {
  Critical: "insight-card__severity--critical",
  High: "insight-card__severity--high",
  Medium: "insight-card__severity--medium",
  Low: "insight-card__severity--low",
};

export default function InsightPanel({ insights }) {
  if (!insights?.length) {
    return <div className="chart-panel__empty">No insights available for the current filters.</div>;
  }

  return (
    <div className="insight-grid">
      {insights.map((insight, i) => (
        <div className="insight-card" key={i}>
          <div className="insight-card__header">
            <span className="insight-card__title">{insight.title}</span>
            <span className={`insight-card__severity ${SEVERITY_CLASS[insight.severity] ?? ""}`}>
              {insight.severity}
            </span>
          </div>
          <div className="insight-card__metric mono">{insight.metric}</div>
          <p className="insight-card__text">{insight.text}</p>
          <p className="insight-card__action">
            <span className="insight-card__action-label">Action:</span> {insight.action}
          </p>
        </div>
      ))}
    </div>
  );
}
