import "./DataQualityReportPanel.css";

function validityStatus(pct) {
  if (pct >= 95) return "good";
  if (pct >= 80) return "warn";
  return "bad";
}

/**
 * Reports on the WHOLE active dataset as ingested - intentionally NOT
 * affected by the dashboard's interactive filters, since this describes
 * a fixed historical fact about how clean the source data was, not a
 * live filtered view.
 */
export default function DataQualityReportPanel({ report, loading }) {
  if (loading) {
    return <div className="chart-panel__empty">Loading data quality report…</div>;
  }
  if (!report) {
    return <div className="chart-panel__empty">No data quality report available.</div>;
  }

  const status = validityStatus(report.data_validity_pct);

  const stats = [
    { label: "Total Records", value: report.total_records },
    { label: "Valid Records", value: report.valid_records },
    { label: "Invalid Records", value: report.invalid_records },
    { label: "Total Hours", value: report.total_hours },
    { label: "Avg Shift Duration", value: `${report.avg_shift_duration_hours}h` },
    { label: "Categories", value: report.category_count },
  ];

  const anomalies = [
    { label: "Zero hours", value: report.anomalies.zero_hours },
    { label: "Negative hours", value: report.anomalies.negative_hours },
    { label: "Outlier hours (95th+ percentile)", value: report.anomalies.outlier_hours_95th_percentile },
    { label: "Duplicate records", value: report.anomalies.duplicate_records },
  ];

  return (
    <div className="quality-report">
      <div className="quality-report__validity">
        <span className="quality-report__validity-label">Data Validity</span>
        <span className={`quality-report__validity-value mono status-${status}`}>
          {report.data_validity_pct}%
        </span>
        <div className="quality-report__gauge">
          <div className={`quality-report__gauge-fill status-${status}`} style={{ width: `${Math.min(report.data_validity_pct, 100)}%` }} />
        </div>
      </div>

      <div className="quality-report__stats-grid">
        {stats.map((s) => (
          <div className="quality-report__stat" key={s.label}>
            <span className="quality-report__stat-label">{s.label}</span>
            <span className="quality-report__stat-value mono">{s.value}</span>
          </div>
        ))}
      </div>

      <div className="quality-report__anomalies">
        <span className="quality-report__anomalies-label">Anomalies Detected</span>
        <ul className="quality-report__anomalies-list">
          {anomalies.map((a) => (
            <li key={a.label} className="quality-report__anomaly-item">
              <span>{a.label}</span>
              <span className={`mono${a.value > 0 ? " quality-report__anomaly-value--flagged" : ""}`}>{a.value}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
