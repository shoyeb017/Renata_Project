import "./InsightPanel.css";

export default function InsightPanel({ insights }) {
  if (!insights?.length) {
    return <div className="chart-panel__empty">No insights available for the current filters.</div>;
  }

  return (
    <ul className="insight-list">
      {insights.map((insight, i) => (
        <li className="insight-item" key={i}>
          <span className="insight-item__index mono">{String(i + 1).padStart(2, "0")}</span>
          <div>
            <span className="insight-item__category">{insight.category}</span>
            <p className="insight-item__text">{insight.text}</p>
          </div>
        </li>
      ))}
    </ul>
  );
}
