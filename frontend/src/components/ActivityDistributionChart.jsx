import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from "recharts";
import "./ChartPanel.css";

function CustomTooltip({ active, payload }) {
  if (!active || !payload?.length) return null;
  const item = payload[0].payload;
  return (
    <div className="chart-tooltip">
      <div className="chart-tooltip__title">{item.activity_name}</div>
      <div className="chart-tooltip__meta mono">{item.hours}h · {item.percentage}%</div>
    </div>
  );
}

export default function ActivityDistributionChart({ distribution }) {
  if (!distribution?.length) {
    return <div className="chart-panel__empty">No activity data for the current filters.</div>;
  }

  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie
          data={distribution}
          dataKey="hours"
          nameKey="activity_name"
          innerRadius={60}
          outerRadius={100}
          paddingAngle={1.5}
          stroke="var(--panel-1)"
          strokeWidth={2}
        >
          {distribution.map((entry) => (
            <Cell key={entry.activity_name} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
      </PieChart>
    </ResponsiveContainer>
  );
}
