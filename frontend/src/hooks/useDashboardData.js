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
 * state and re-fetches every FILTER-AWARE endpoint whenever filters
 * change. The whole-dataset panels (Breakdown Streaks, Data Quality
 * Report) are fetched separately and only re-fetched when the active
 * dataset itself changes (upload/activate) - never on filter changes -
 * since they're defined to ignore filters entirely.
 */
export function useDashboardData() {
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [filterOptions, setFilterOptions] = useState(null);
  const [summary, setSummary] = useState(null);
  const [shiftBlocks, setShiftBlocks] = useState([]);
  const [distribution, setDistribution] = useState([]);
  const [trend, setTrend] = useState([]);
  const [streaks, setStreaks] = useState({ streaks: [], timeline: [], config: null });
  const [qualityReport, setQualityReport] = useState(null);
  const [insights, setInsights] = useState([]);
  const [datasets, setDatasets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [wholeDatasetLoading, setWholeDatasetLoading] = useState(true);
  const [error, setError] = useState(null);
  const [uploadState, setUploadState] = useState({ status: "idle", message: "" });

  // Bumped whenever the active dataset changes (upload/activate), to
  // trigger a re-fetch of both the filter-aware and whole-dataset data.
  const [datasetVersion, setDatasetVersion] = useState(0);

  const refreshDatasetList = useCallback(() => {
    api.listDatasets().then((res) => setDatasets(res.datasets)).catch(() => {});
  }, []);

  useEffect(() => {
    refreshDatasetList();
  }, [refreshDatasetList, datasetVersion]);

  useEffect(() => {
    api.getFilterOptions().then(setFilterOptions).catch((err) => setError(err.message));
  }, [datasetVersion]);

  const refetchFilterAware = useCallback(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      api.getDashboardSummary(filters),
      api.getShiftAnalysis(filters),
      api.getActivityDistribution(filters),
      api.getBreakdownTrend(filters),
      api.getInsights(filters),
    ])
      .then(([summaryRes, shiftRes, distRes, trendRes, insightsRes]) => {
        setSummary(summaryRes);
        setShiftBlocks(shiftRes.blocks);
        setDistribution(distRes.distribution);
        setTrend(trendRes.trend);
        setInsights(insightsRes.insights);
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, [filters, datasetVersion]);

  const refetchWholeDataset = useCallback(() => {
    setWholeDatasetLoading(true);
    Promise.all([api.getBreakdownStreaks(), api.getDataQualityReport()])
      .then(([streaksRes, qualityRes]) => {
        setStreaks(streaksRes);
        setQualityReport(qualityRes);
      })
      .catch((err) => setError(err.message))
      .finally(() => setWholeDatasetLoading(false));
  }, [datasetVersion]);

  useEffect(() => {
    refetchFilterAware();
  }, [refetchFilterAware]);

  useEffect(() => {
    refetchWholeDataset();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [datasetVersion]);

  const resetFilters = useCallback(() => setFilters(EMPTY_FILTERS), []);

  const uploadDataset = useCallback((file) => {
    setUploadState({ status: "uploading", message: `Processing ${file.name}…` });
    return api
      .uploadDataset(file)
      .then((result) => {
        setUploadState({
          status: "success",
          message: `Loaded "${file.name}" — ${result.report.final_clean_records} clean records.`,
        });
        setFilters(EMPTY_FILTERS);
        setDatasetVersion((v) => v + 1);
        return result;
      })
      .catch((err) => {
        setUploadState({ status: "error", message: err.message });
        throw err;
      });
  }, []);

  const activateDataset = useCallback((datasetId) => {
    return api.activateDataset(datasetId).then((result) => {
      setFilters(EMPTY_FILTERS);
      setDatasetVersion((v) => v + 1);
      return result;
    });
  }, []);

  return {
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
  };
}
