import { useState } from "react";
import "./FilterPanel.css";

function MultiToggle({ options, selected, onToggle }) {
  return (
    <div className="filter-chip-group">
      {options.map((opt) => {
        const isActive = selected.includes(opt);
        return (
          <button
            key={opt}
            type="button"
            className={`filter-chip${isActive ? " filter-chip--active" : ""}`}
            onClick={() => onToggle(opt)}
            aria-pressed={isActive}
          >
            {opt}
          </button>
        );
      })}
    </div>
  );
}

export default function FilterPanel({ filters, setFilters, filterOptions, onReset }) {
  const [expanded, setExpanded] = useState(true);

  if (!filterOptions) {
    return <div className="filter-panel filter-panel--loading">Loading filters…</div>;
  }

  const toggleReason = (reason) => {
    setFilters((prev) => {
      const reasons = prev.reasons.includes(reason)
        ? prev.reasons.filter((r) => r !== reason)
        : [...prev.reasons, reason];
      return { ...prev, reasons };
    });
  };

  const toggleCategory = (category) => {
    setFilters((prev) => {
      const categories = prev.categories.includes(category)
        ? prev.categories.filter((c) => c !== category)
        : [...prev.categories, category];
      return { ...prev, categories };
    });
  };

  const activeFilterCount =
    (filters.dateFrom ? 1 : 0) +
    (filters.dateTo ? 1 : 0) +
    filters.reasons.length +
    filters.categories.length +
    (filters.minDuration ? 1 : 0) +
    (filters.maxDuration ? 1 : 0);

  return (
    <div className="filter-panel">
      <button className="filter-panel__header" onClick={() => setExpanded((e) => !e)}>
        <span className="filter-panel__title">Filters</span>
        {activeFilterCount > 0 && <span className="filter-panel__badge mono">{activeFilterCount}</span>}
        <span className="filter-panel__chevron">{expanded ? "▾" : "▸"}</span>
      </button>

      {expanded && (
        <div className="filter-panel__body">
          <div className="filter-group">
            <label className="filter-group__label">Date range</label>
            <div className="filter-group__row">
              <input
                type="date"
                className="filter-input"
                value={filters.dateFrom}
                min={filterOptions.date_bounds?.min}
                max={filterOptions.date_bounds?.max}
                onChange={(e) => setFilters((prev) => ({ ...prev, dateFrom: e.target.value }))}
              />
              <span className="filter-group__sep">to</span>
              <input
                type="date"
                className="filter-input"
                value={filters.dateTo}
                min={filterOptions.date_bounds?.min}
                max={filterOptions.date_bounds?.max}
                onChange={(e) => setFilters((prev) => ({ ...prev, dateTo: e.target.value }))}
              />
            </div>
          </div>

          <div className="filter-group">
            <label className="filter-group__label">Duration range (h)</label>
            <div className="filter-group__row">
              <input
                type="number"
                step="0.1"
                placeholder={String(filterOptions.duration_bounds?.min ?? 0)}
                className="filter-input filter-input--narrow"
                value={filters.minDuration}
                onChange={(e) => setFilters((prev) => ({ ...prev, minDuration: e.target.value }))}
              />
              <span className="filter-group__sep">to</span>
              <input
                type="number"
                step="0.1"
                placeholder={String(filterOptions.duration_bounds?.max ?? 0)}
                className="filter-input filter-input--narrow"
                value={filters.maxDuration}
                onChange={(e) => setFilters((prev) => ({ ...prev, maxDuration: e.target.value }))}
              />
            </div>
          </div>

          <div className="filter-group">
            <label className="filter-group__label">Category</label>
            <MultiToggle
              options={filterOptions.categories}
              selected={filters.categories}
              onToggle={toggleCategory}
            />
          </div>

          <div className="filter-group">
            <label className="filter-group__label">Activity reason</label>
            <MultiToggle
              options={filterOptions.reasons}
              selected={filters.reasons}
              onToggle={toggleReason}
            />
          </div>

          {activeFilterCount > 0 && (
            <button type="button" className="filter-reset" onClick={onReset}>
              Clear all filters
            </button>
          )}
        </div>
      )}
    </div>
  );
}
