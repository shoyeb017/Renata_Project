import { useDashboardData } from "../hooks/useDashboardData";
import AppHeader from "../components/AppHeader";
import KpiCards from "../components/KpiCards";
import FilterPanel from "../components/FilterPanel";
import DatasetPanel from "../components/DatasetPanel";
import ActivityLegend from "../components/ActivityLegend";
import ShiftAnalysisChart from "../components/ShiftAnalysisChart";
import ActivityDistributionChart from "../components/ActivityDistributionChart";
import BreakdownTrendChart from "../components/BreakdownTrendChart";
import BreakdownStreaksPanel from "../components/BreakdownStreaksPanel";
import DataQualityReportPanel from "../components/DataQualityReportPanel";
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
    streaks,
    qualityReport,
    insights,
    datasets,
    loading,
    wholeDatasetLoading,
    error,
    uploadState,
    uploadDataset,
    activateDataset,
  } = useDashboardData();

  return (
    <div className="dashboard">
      <AppHeader dateRange={summary?.date_range} />

      <div className="dashboard__body">
        <aside className="dashboard__sidebar">
          <DatasetPanel
            datasets={datasets}
            uploadState={uploadState}
            onUpload={uploadDataset}
            onActivate={activateDataset}
          />
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

          <section className="dashboard__panel">
            <div className="dashboard__panel-header">
              <h2 className="dashboard__panel-title">Breakdown Streaks</h2>
              <span className="dashboard__panel-badge">Whole dataset · not filtered</span>
            </div>
            <BreakdownStreaksPanel
              streaks={streaks.streaks}
              timeline={streaks.timeline}
              config={streaks.config}
              loading={wholeDatasetLoading}
            />
          </section>

          <section className="dashboard__panel">
            <div className="dashboard__panel-header">
              <h2 className="dashboard__panel-title">Data Quality Report</h2>
              <span className="dashboard__panel-badge">Whole dataset · not filtered</span>
            </div>
            <DataQualityReportPanel report={qualityReport} loading={wholeDatasetLoading} />
          </section>

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
