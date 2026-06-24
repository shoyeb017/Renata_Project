import { useEffect, useState, useCallback } from "react";
import { api } from "../api/client";

const EMPTY_FILTERS = {
  dateFrom: "",
  dateTo: "",
  reasons: [],
  categories: [],
  minDuration: "",
  maxDuration: "",
};

/**
 * Central data-fetching hook for the dashboard. Holds the active filter
 * state and re-fetches every endpoint whenever filters change, so all
 * charts and KPIs stay in sync with one source of truth.
 */
export function useDashboardData() {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [filterOptions, setFilterOptions] = useState(null);
  const [summary, setSummary] = useState(null);
  const [shiftBlocks, setShiftBlocks] = useState([]);
  const [distribution, setDistribution] = useState([]);
  const [trend, setTrend] = useState([]);
  const [heatmap, setHeatmap] = useState([]);
  const [streaks, setStreaks] = useState({ streaks: [], config: null });
  const [insights, setInsights] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.getFilterOptions().then(setFilterOptions).catch((err) => setError(err.message));
  }, []);

  const refetch = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      api.getDashboardSummary(filters),
      api.getShiftAnalysis(filters),
      api.getActivityDistribution(filters),
      api.getBreakdownTrend(filters),
      api.getFailureHeatmap(filters),
      api.getBreakdownStreaks(filters),
      api.getInsights(filters),
    ])
      .then(([summaryRes, shiftRes, distRes, trendRes, heatmapRes, streaksRes, insightsRes]) => {
        setSummary(summaryRes);
        setShiftBlocks(shiftRes.blocks);
        setDistribution(distRes.distribution);
        setTrend(trendRes.trend);
        setHeatmap(heatmapRes.heatmap);
        setStreaks(streaksRes);
        setInsights(insightsRes.insights);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [filters]);

  useEffect(() => {
    refetch();
  }, [refetch]);

  const resetFilters = useCallback(() => setFilters(EMPTY_FILTERS), []);

  return {
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
  };
}
