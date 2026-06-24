import { useMemo, useState } from "react";
import "./BreakdownStreaksPanel.css";

const CHART_HEIGHT = 160;
const CHART_PADDING_LEFT = 40;

function formatDateLabel(dateStr) {
  const d = new Date(`${dateStr}T00:00:00`);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

const SEVERITY_COLOR = {
  Critical: "var(--status-bad)",
  High: "#D9714A",
  Medium: "var(--status-warn)",
  Low: "var(--text-tertiary)",
};

/**
 * Visualizes failure hours across the WHOLE active dataset (the `timeline`
 * prop), with detected streak date-ranges highlighted as shaded bands
 * behind the bars. This view is intentionally NOT affected by the
 * dashboard's interactive filters - it always reflects breakdown risk
 * across the complete dataset, per design.
 */
export default function BreakdownStreaksPanel({ streaks, timeline, config, loading }) {
  const [selectedIndex, setSelectedIndex] = useState(0);

  const { bars, maxHours, streakDateSet } = useMemo(() => {
    const max = Math.max(...timeline.map((t) => t.failure_hours), 1);
    const streakDates = new Set();
    streaks.forEach((s) => {
      let cursor = new Date(`${s.start_date}T00:00:00`);
      const end = new Date(`${s.end_date}T00:00:00`);
      while (cursor <= end) {
        streakDates.add(cursor.toISOString().slice(0, 10));
        cursor.setDate(cursor.getDate() + 1);
      }
    });
    return { bars: timeline, maxHours: max, streakDateSet: streakDates };
  }, [timeline, streaks]);

  if (loading) {
    return <div className="chart-panel__empty">Loading breakdown streak data…</div>;
  }

  if (!timeline.length) {
    return <div className="chart-panel__empty">No failure events recorded in this dataset.</div>;
  }

  const barWidth = Math.max(900 / bars.length, 18);
  const chartWidth = barWidth * bars.length + CHART_PADDING_LEFT;
  const selected = streaks[selectedIndex];

  return (
    <div className="streaks-panel">
      {config && (
        <p className="streaks-panel__config mono">
          Whole-dataset view (not affected by filters) · streak rule: ≥{config.minimum_events} events,
          ≥{config.minimum_hours}h total, gaps ≤{config.max_gap_hours}h
        </p>
      )}

      <div className="streaks-panel__chart-scroll">
        <svg width={chartWidth} height={CHART_HEIGHT + 24} className="streaks-panel__svg" role="img" aria-label="Breakdown streak timeline">
          {bars.map((bar, i) => {
            const x = CHART_PADDING_LEFT + i * barWidth;
            const isStreakDay = streakDateSet.has(bar.date);
            const barHeight = (bar.failure_hours / maxHours) * (CHART_HEIGHT - 20);
            return (
              <g key={bar.date}>
                {isStreakDay && (
                  <rect
                    x={x}
                    y={0}
                    width={barWidth}
                    height={CHART_HEIGHT}
                    fill="var(--status-bad)"
                    opacity={0.08}
                  />
                )}
                <rect
                  x={x + barWidth * 0.18}
                  y={CHART_HEIGHT - barHeight}
                  width={barWidth * 0.64}
                  height={Math.max(barHeight, 1)}
                  fill={isStreakDay ? "var(--status-bad)" : "var(--text-tertiary)"}
                  opacity={isStreakDay ? 0.9 : 0.45}
                  rx={1}
                />
                <text
                  x={x + barWidth / 2}
                  y={CHART_HEIGHT + 16}
                  textAnchor="middle"
                  className="streaks-panel__x-label"
                >
                  {formatDateLabel(bar.date)}
                </text>
              </g>
            );
          })}
          <line
            x1={CHART_PADDING_LEFT}
            x2={chartWidth}
            y1={CHART_HEIGHT}
            y2={CHART_HEIGHT}
            className="streaks-panel__axis-line"
          />
        </svg>
      </div>

      <div className="streaks-panel__legend">
        <span className="streaks-panel__legend-item">
          <span className="streaks-panel__legend-swatch streaks-panel__legend-swatch--streak" /> Within a detected streak
        </span>
        <span className="streaks-panel__legend-item">
          <span className="streaks-panel__legend-swatch" /> Isolated failure
        </span>
      </div>

      {!streaks.length ? (
        <div className="chart-panel__empty">
          No breakdown streaks detected for the current thresholds.
        </div>
      ) : (
        <>
          <div className="streaks-panel__tabs">
            {streaks.map((s, i) => (
              <button
                key={i}
                type="button"
                className={`streaks-panel__tab${i === selectedIndex ? " streaks-panel__tab--active" : ""}`}
                onClick={() => setSelectedIndex(i)}
                style={i === selectedIndex ? { borderColor: SEVERITY_COLOR[s.severity] } : undefined}
              >
                {s.start_date}
                <span
                  className="streaks-panel__tab-severity"
                  style={{ color: SEVERITY_COLOR[s.severity] }}
                >
                  {s.severity}
                </span>
              </button>
            ))}
          </div>

          {selected && (
            <div className="streaks-detail">
              <div className="streaks-detail__header">
                <span className="streaks-detail__title">Detailed Breakdown Streak</span>
                <span
                  className="streaks-detail__severity-badge"
                  style={{
                    color: SEVERITY_COLOR[selected.severity],
                    borderColor: SEVERITY_COLOR[selected.severity],
                  }}
                >
                  {selected.severity}
                </span>
              </div>
              <div className="streaks-detail__grid">
                <div className="streaks-detail__field">
                  <span className="streaks-detail__label">Start Date</span>
                  <span className="streaks-detail__value mono">{selected.start_date}</span>
                </div>
                <div className="streaks-detail__field">
                  <span className="streaks-detail__label">End Date</span>
                  <span className="streaks-detail__value mono">{selected.end_date}</span>
                </div>
                <div className="streaks-detail__field">
                  <span className="streaks-detail__label">Duration (Days)</span>
                  <span className="streaks-detail__value mono">{selected.duration_days}</span>
                </div>
                <div className="streaks-detail__field">
                  <span className="streaks-detail__label">Total Hours</span>
                  <span className="streaks-detail__value mono">{selected.total_hours}</span>
                </div>
                <div className="streaks-detail__field">
                  <span className="streaks-detail__label">Avg/Day</span>
                  <span className="streaks-detail__value mono">{selected.avg_hours_per_day}</span>
                </div>
                <div className="streaks-detail__field">
                  <span className="streaks-detail__label">Severity</span>
                  <span className="streaks-detail__value" style={{ color: SEVERITY_COLOR[selected.severity] }}>
                    {selected.severity}
                  </span>
                </div>
              </div>
              <div className="streaks-detail__activities">
                <span className="streaks-detail__label">Activities involved</span>
                <span className="streaks-detail__value">{selected.activities.join(", ")}</span>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
