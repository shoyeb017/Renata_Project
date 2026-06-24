import { Fragment, useMemo } from "react";
import "./FailureHeatmap.css";

const DAY_ORDER = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

function colorForIntensity(value, max) {
  if (max === 0 || value === 0) return "transparent";
  const intensity = Math.min(value / max, 1);
  // Interpolate from a dim red to the full failure-red accent.
  const alpha = 0.15 + intensity * 0.75;
  return `rgba(196, 69, 54, ${alpha.toFixed(2)})`;
}

export default function FailureHeatmap({ heatmap }) {
  const { buckets, grid, maxValue, daysPresent } = useMemo(() => {
    if (!heatmap?.length) return { buckets: [], grid: {}, maxValue: 0, daysPresent: [] };

    const bucketSet = new Set();
    const dayBucketGrid = {};
    let max = 0;

    heatmap.forEach((cell) => {
      bucketSet.add(cell.hour_bucket_start);
      dayBucketGrid[`${cell.day_of_week}-${cell.hour_bucket_start}`] = cell;
      max = Math.max(max, cell.failure_hours);
    });

    const buckets = Array.from(bucketSet).sort((a, b) => a - b);
    const daysPresent = DAY_ORDER.filter((day) => heatmap.some((c) => c.day_of_week === day));

    return { buckets, grid: dayBucketGrid, maxValue: max, daysPresent };
  }, [heatmap]);

  if (!heatmap?.length) {
    return <div className="chart-panel__empty">No failure events for the current filters.</div>;
  }

  return (
    <div className="heatmap">
      <div className="heatmap__grid" style={{ gridTemplateColumns: `64px repeat(${buckets.length}, 1fr)` }}>
        <div className="heatmap__corner" />
        {buckets.map((b) => (
          <div className="heatmap__col-label" key={b}>
            {String(b).padStart(2, "0")}h
          </div>
        ))}

        {daysPresent.map((day) => (
          <Fragment key={day}>
            <div className="heatmap__row-label">{day.slice(0, 3)}</div>
            {buckets.map((b) => {
              const cell = grid[`${day}-${b}`];
              const value = cell?.failure_hours ?? 0;
              return (
                <div
                  className="heatmap__cell"
                  key={`${day}-${b}`}
                  style={{ background: colorForIntensity(value, maxValue) }}
                  title={cell ? `${day}, ${cell.hour_bucket_label}: ${value}h failure time` : `${day}: no failures`}
                >
                  {value > 0 && <span className="heatmap__cell-value mono">{value}</span>}
                </div>
              );
            })}
          </Fragment>
        ))}
      </div>
    </div>
  );
}
