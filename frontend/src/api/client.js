/**
 * Thin REST client for the Shift Analytics API.
 *
 * Base URL comes from VITE_API_BASE_URL (see .env.example), defaulting to
 * the local Django dev server. All dashboard data flows through these
 * functions so components never construct fetch calls inline.
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api";

async function get(path, params = {}) {
  const url = new URL(`${API_BASE_URL}${path}`);
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== "") {
      url.searchParams.set(key, value);
    }
  });
  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error(`API request failed: ${response.status} ${response.statusText} (${url})`);
  }
  return response.json();
}

export function buildFilterParams(filters) {
  const params = {};
  if (filters.dateFrom) params.date_from = filters.dateFrom;
  if (filters.dateTo) params.date_to = filters.dateTo;
  if (filters.reasons?.length) params.reason = filters.reasons.join(",");
  if (filters.categories?.length) params.category = filters.categories.join(",");
  if (filters.minDuration !== undefined && filters.minDuration !== "") params.min_duration = filters.minDuration;
  if (filters.maxDuration !== undefined && filters.maxDuration !== "") params.max_duration = filters.maxDuration;
  return params;
}

export const api = {
  getDashboardSummary: (filters) => get("/dashboard-summary", buildFilterParams(filters)),
  getShiftAnalysis: (filters) => get("/shift-analysis", buildFilterParams(filters)),
  getActivityDistribution: (filters) => get("/activity-distribution", buildFilterParams(filters)),
  getBreakdownTrend: (filters) => get("/breakdown-trend", buildFilterParams(filters)),
  getFailureHeatmap: (filters) => get("/failure-heatmap", buildFilterParams(filters)),
  getBreakdownStreaks: (filters) => get("/breakdown-streaks", buildFilterParams(filters)),
  getInsights: (filters) => get("/insights", buildFilterParams(filters)),
  getFilterOptions: () => get("/filter-options"),
};
