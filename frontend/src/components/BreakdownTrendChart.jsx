import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import "./ChartPanel.css";

function formatDateTick(dateStr) {
  const d = new Date(`${dateStr}T00:00:00`);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip__title">{formatDateTick(label)}</div>
      <div className="chart-tooltip__meta mono">{payload[0].value}h failure time</div>
    </div>
  );
}

export default function BreakdownTrendChart({ trend }) {
  if (!trend?.length) {
    return <div className="chart-panel__empty">No failure events for the current filters.</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={trend} margin={{ top: 8, right: 12, bottom: 0, left: -8 }}>
        <defs>
          <linearGradient id="failureFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--status-bad)" stopOpacity={0.45} />
            <stop offset="100%" stopColor="var(--status-bad)" stopOpacity={0.03} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke="var(--hairline)" vertical={false} />
        <XAxis
          dataKey="date"
          tickFormatter={formatDateTick}
          stroke="var(--hairline-strong)"
          tick={{ fill: "var(--text-tertiary)", fontSize: 10, fontFamily: "var(--font-mono)" }}
        />
        <YAxis
          stroke="var(--hairline-strong)"
          tick={{ fill: "var(--text-tertiary)", fontSize: 10, fontFamily: "var(--font-mono)" }}
          width={32}
        />
        <Tooltip content={<CustomTooltip />} />
        <Area
          type="monotone"
          dataKey="failure_hours"
          stroke="var(--status-bad)"
          strokeWidth={2}
          fill="url(#failureFill)"
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
