import { useMemo, useState } from "react";
import "./ShiftAnalysisChart.css";

const CHART_HEIGHT = 480;
const Y_MIN_HOUR = 0;
const Y_MAX_HOUR = 36;
const ROW_LABEL_WIDTH = 64;
const DAY_COLUMN_MIN_WIDTH = 56;

/**
 * Primary "Shift Analysis Chart" - a timeline/Gantt-style visualization,
 * NOT a bar chart, per the spec.
 *
 * X-axis: each distinct date present in the (filtered) dataset, in order.
 * Y-axis: a continuous 0-36 hour scale so shifts crossing midnight render
 *         as one continuous block instead of wrapping/clipping. Hour 24
 *         on the scale is "next midnight"; hours 24-36 cover the early
 *         morning of the following day, which is why the required labels
 *         include "Next 3 AM" through "Next 12 PM".
 *
 * Each activity record is drawn as a rectangle: x = its date's column,
 * y = its start hour, height = its duration. Color and category come
 * entirely from the API response (which itself reads ActivityConfiguration),
 * so nothing here hardcodes an activity name.
 */

const Y_AXIS_LABELS = [
  { hour: 0, label: "12 AM" },
  { hour: 3, label: "3 AM" },
  { hour: 6, label: "6 AM" },
  { hour: 9, label: "9 AM" },
  { hour: 12, label: "12 PM" },
  { hour: 15, label: "3 PM" },
  { hour: 18, label: "6 PM" },
  { hour: 21, label: "9 PM" },
  { hour: 24, label: "Next 12 AM" },
  { hour: 27, label: "Next 3 AM" },
  { hour: 30, label: "Next 6 AM" },
  { hour: 33, label: "Next 9 AM" },
  { hour: 36, label: "Next 12 PM" },
];

function hourToY(hour, plotHeight) {
  const clamped = Math.max(Y_MIN_HOUR, Math.min(Y_MAX_HOUR, hour));
  const fraction = (clamped - Y_MIN_HOUR) / (Y_MAX_HOUR - Y_MIN_HOUR);
  return plotHeight - fraction * plotHeight;
}

function formatDateLabel(dateStr) {
  const d = new Date(`${dateStr}T00:00:00`);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

export default function ShiftAnalysisChart({ blocks }) {
  const [hovered, setHovered] = useState(null);

  const dates = useMemo(() => {
    const unique = Array.from(new Set(blocks.map((b) => b.date)));
    return unique.sort();
  }, [blocks]);

  const plotHeight = CHART_HEIGHT;
  const columnWidth = Math.max(DAY_COLUMN_MIN_WIDTH, 900 / Math.max(dates.length, 1));
  const plotWidth = columnWidth * Math.max(dates.length, 1);
  const totalWidth = plotWidth + ROW_LABEL_WIDTH;

  const dateIndex = useMemo(() => {
    const map = {};
    dates.forEach((d, i) => (map[d] = i));
    return map;
  }, [dates]);

  if (blocks.length === 0) {
    return (
      <div className="shift-chart shift-chart--empty">
        No shift records match the current filters.
      </div>
    );
  }

  return (
    <div className="shift-chart">
      <div className="shift-chart__scroll">
        <svg
          width={totalWidth}
          height={plotHeight + 40}
          className="shift-chart__svg"
          role="img"
          aria-label="Shift analysis timeline chart"
        >
          {/* Y-axis grid lines + labels */}
          {Y_AXIS_LABELS.map(({ hour, label }) => {
            const y = hourToY(hour, plotHeight);
            return (
              <g key={hour}>
                <line
                  x1={ROW_LABEL_WIDTH}
                  x2={totalWidth}
                  y1={y}
                  y2={y}
                  className={hour === 24 ? "shift-chart__gridline--midnight" : "shift-chart__gridline"}
                />
                <text x={ROW_LABEL_WIDTH - 8} y={y} className="shift-chart__y-label" textAnchor="end" dy="3">
                  {label}
                </text>
              </g>
            );
          })}

          {/* Day column separators + x-axis labels */}
          {dates.map((date, i) => {
            const x = ROW_LABEL_WIDTH + i * columnWidth;
            return (
              <g key={date}>
                <line
                  x1={x}
                  x2={x}
                  y1={0}
                  y2={plotHeight}
                  className="shift-chart__gridline-vertical"
                />
                <text
                  x={x + columnWidth / 2}
                  y={plotHeight + 20}
                  className="shift-chart__x-label"
                  textAnchor="middle"
                >
                  {formatDateLabel(date)}
                </text>
              </g>
            );
          })}
          <line
            x1={ROW_LABEL_WIDTH + plotWidth}
            x2={ROW_LABEL_WIDTH + plotWidth}
            y1={0}
            y2={plotHeight}
            className="shift-chart__gridline-vertical"
          />

          {/* Activity blocks */}
          {blocks.map((block) => {
            const colIndex = dateIndex[block.date];
            if (colIndex === undefined) return null;
            const x = ROW_LABEL_WIDTH + colIndex * columnWidth + columnWidth * 0.12;
            const blockWidth = columnWidth * 0.76;
            const yTop = hourToY(block.end_hour, plotHeight);
            const yBottom = hourToY(block.start_hour, plotHeight);
            const height = Math.max(yBottom - yTop, 2);
            const isHovered = hovered?.id === block.id;

            return (
              <rect
                key={block.id}
                x={x}
                y={yTop}
                width={blockWidth}
                height={height}
                fill={block.color}
                opacity={isHovered ? 1 : 0.88}
                stroke={isHovered ? "var(--text-primary)" : "transparent"}
                strokeWidth={isHovered ? 1.5 : 0}
                rx={1.5}
                className="shift-chart__block"
                onMouseEnter={() => setHovered(block)}
                onMouseLeave={() => setHovered(null)}
              />
            );
          })}
        </svg>
      </div>

      {hovered && (
        <div className="shift-chart__tooltip">
          <span className="shift-chart__tooltip-swatch" style={{ background: hovered.color }} />
          <div>
            <div className="shift-chart__tooltip-title">{hovered.activity_name}</div>
            <div className="shift-chart__tooltip-meta mono">
              {formatDateLabel(hovered.date)} · {hovered.start_label}–{hovered.end_label} · {hovered.duration_hours}h
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
