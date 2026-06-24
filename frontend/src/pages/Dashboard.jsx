import { useDashboardData } from "../hooks/useDashboardData";
import AppHeader from "../components/AppHeader";
import KpiCards from "../components/KpiCards";
import FilterPanel from "../components/FilterPanel";
import ActivityLegend from "../components/ActivityLegend";
import ShiftAnalysisChart from "../components/ShiftAnalysisChart";
import ActivityDistributionChart from "../components/ActivityDistributionChart";
import BreakdownTrendChart from "../components/BreakdownTrendChart";
import FailureHeatmap from "../components/FailureHeatmap";
import BreakdownStreaks from "../components/BreakdownStreaks";
import InsightPanel from "../components/InsightPanel";
import "./Dashboard.css";

export default function Dashboard() {
  const {
    filters,
    setFilters,
    resetFilters,
    filterOptions,
    summary,
    shiftBlocks,
    distribution,
    trend,
    heatmap,
    streaks,
    insights,
    loading,
    error,
  } = useDashboardData();

  return (
    <div className="dashboard">
      <AppHeader dateRange={summary?.date_range} />

      <div className="dashboard__body">
        <aside className="dashboard__sidebar">
          <FilterPanel
            filters={filters}
            setFilters={setFilters}
            filterOptions={filterOptions}
            onReset={resetFilters}
          />
        </aside>

        <main className="dashboard__main">
          {error && <div className="dashboard__error">Couldn't load dashboard data: {error}</div>}

          <KpiCards summary={summary} />

          <section className="dashboard__panel">
            <div className="dashboard__panel-header">
              <h2 className="dashboard__panel-title">Shift Analysis</h2>
            </div>
            <ShiftAnalysisChart blocks={shiftBlocks} />
            <ActivityLegend activityConfigs={filterOptions?.activity_configs} />
          </section>

          <div className="dashboard__grid-2">
            <section className="dashboard__panel">
              <h2 className="dashboard__panel-title">Activity Distribution</h2>
              <ActivityDistributionChart distribution={distribution} />
            </section>

            <section className="dashboard__panel">
              <h2 className="dashboard__panel-title">Breakdown Trend</h2>
              <BreakdownTrendChart trend={trend} />
            </section>
          </div>

          <div className="dashboard__grid-2">
            <section className="dashboard__panel">
              <h2 className="dashboard__panel-title">Failure Heatmap</h2>
              <FailureHeatmap heatmap={heatmap} />
            </section>

            <section className="dashboard__panel">
              <h2 className="dashboard__panel-title">Breakdown Streaks</h2>
              <BreakdownStreaks streaks={streaks} />
            </section>
          </div>

          <section className="dashboard__panel">
            <h2 className="dashboard__panel-title">Operational Insights</h2>
            <InsightPanel insights={insights} />
          </section>

          {loading && <div className="dashboard__loading-bar" aria-hidden="true" />}
        </main>
      </div>
    </div>
  );
}
