import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import DataQualityReportPanel from '../components/DataQualityReportPanel';

const sampleReport = {
  data_validity_pct: 98.0,
  total_records: 51,
  valid_records: 50,
  invalid_records: 0,
  total_hours: 143.5,
  avg_shift_duration_hours: 2.87,
  category_count: 6,
  anomalies: {
    zero_hours: 0,
    negative_hours: 1,
    outlier_hours_95th_percentile: 3,
    duplicate_records: 1,
  },
};

describe('DataQualityReportPanel', () => {
  it('shows a loading state', () => {
    render(<DataQualityReportPanel report={null} loading={true} />);
    expect(screen.getByText(/loading data quality report/i)).toBeInTheDocument();
  });

  it('renders the validity percentage and core metrics', () => {
    render(<DataQualityReportPanel report={sampleReport} loading={false} />);
    expect(screen.getByText('98%')).toBeInTheDocument();
    expect(screen.getByText('51')).toBeInTheDocument();
    expect(screen.getByText('Categories')).toBeInTheDocument();
  });

  it('renders all four anomaly counters', () => {
    render(<DataQualityReportPanel report={sampleReport} loading={false} />);
    expect(screen.getByText('Zero hours')).toBeInTheDocument();
    expect(screen.getByText('Negative hours')).toBeInTheDocument();
    expect(screen.getByText('Outlier hours (95th+ percentile)')).toBeInTheDocument();
    expect(screen.getByText('Duplicate records')).toBeInTheDocument();
  });
});
