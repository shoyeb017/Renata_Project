import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import FilterPanel from '../components/FilterPanel';

const filterOptions = {
  reasons: ['Training', 'Breakdown'],
  categories: ['Productive', 'Failure'],
  duration_bounds: { min: 0.5, max: 18 },
  date_bounds: { min: '2025-10-01', max: '2025-10-21' },
  activity_configs: [],
};

const emptyFilters = {
  dateFrom: '',
  dateTo: '',
  reasons: [],
  categories: [],
  minDuration: '',
  maxDuration: '',
};

describe('FilterPanel', () => {
  it('shows a loading state until filter options arrive', () => {
    render(
      <FilterPanel filters={emptyFilters} setFilters={() => {}} filterOptions={null} onReset={() => {}} />,
    );
    expect(screen.getByText(/loading filters/i)).toBeInTheDocument();
  });

  it('renders dynamic reason and category chips from filterOptions, not a fixed list', () => {
    render(
      <FilterPanel filters={emptyFilters} setFilters={() => {}} filterOptions={filterOptions} onReset={() => {}} />,
    );
    expect(screen.getByText('Training')).toBeInTheDocument();
    expect(screen.getByText('Breakdown')).toBeInTheDocument();
    expect(screen.getByText('Productive')).toBeInTheDocument();
    expect(screen.getByText('Failure')).toBeInTheDocument();
  });

  it('toggles a reason chip and calls setFilters with the updated selection', () => {
    const setFilters = vi.fn();
    render(
      <FilterPanel filters={emptyFilters} setFilters={setFilters} filterOptions={filterOptions} onReset={() => {}} />,
    );
    fireEvent.click(screen.getByText('Breakdown'));
    expect(setFilters).toHaveBeenCalled();
    const updateFn = setFilters.mock.calls[0][0];
    const result = updateFn(emptyFilters);
    expect(result.reasons).toContain('Breakdown');
  });

  it('shows a reset button only when filters are active', () => {
    const { rerender } = render(
      <FilterPanel filters={emptyFilters} setFilters={() => {}} filterOptions={filterOptions} onReset={() => {}} />,
    );
    expect(screen.queryByText(/clear all filters/i)).not.toBeInTheDocument();

    rerender(
      <FilterPanel
        filters={{ ...emptyFilters, reasons: ['Breakdown'] }}
        setFilters={() => {}}
        filterOptions={filterOptions}
        onReset={() => {}}
      />,
    );
    expect(screen.getByText(/clear all filters/i)).toBeInTheDocument();
  });
});
