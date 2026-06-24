import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import KpiCards from '../components/KpiCards';

const sampleSummary = {
  total_hours: 100,
  productive_hours: 70,
  downtime_hours: 30,
  efficiency_score: 70,
  record_count: 42,
  date_range: { start: '2025-10-01', end: '2025-10-21' },
};

describe('KpiCards', () => {
  it('renders nothing when summary is not yet loaded', () => {
    const { container } = render(<KpiCards summary={null} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders the efficiency score and KPI values from props', () => {
    render(<KpiCards summary={sampleSummary} />);
    expect(screen.getAllByText('70').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('100')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
  });

  it('labels the hero metric as Operational Efficiency Score', () => {
    render(<KpiCards summary={sampleSummary} />);
    expect(screen.getByText(/operational efficiency score/i)).toBeInTheDocument();
  });
});
