import "./BreakdownStreaks.css";

export default function BreakdownStreaks({ streaks }) {
  const { streaks: items, config } = streaks || {};

  return (
    <div>
      {config && (
        <p className="streaks__config mono">
          Streak rule: ≥{config.minimum_events} events, ≥{config.minimum_hours}h total,
          gaps ≤{config.max_gap_hours}h
        </p>
      )}
      {!items?.length ? (
        <div className="chart-panel__empty">
          No breakdown streaks detected for the current filters and thresholds.
        </div>
      ) : (
        <ul className="streaks__list">
          {items.map((streak, i) => (
            <li className="streaks__item" key={i}>
              <div className="streaks__item-header">
                <span className="streaks__item-window mono">
                  {streak.start_time} → {streak.end_time}
                </span>
                <span className="streaks__item-duration mono">{streak.total_duration_hours}h</span>
              </div>
              <div className="streaks__item-meta">
                {streak.event_count} events · {streak.activities.join(", ")}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
