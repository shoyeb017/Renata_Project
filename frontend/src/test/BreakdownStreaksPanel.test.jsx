import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import BreakdownStreaksPanel from '../components/BreakdownStreaksPanel';

const sampleStreaks = [
  {
    start_date: '2025-10-08',
    end_date: '2025-10-09',
    duration_days: 2,
    event_count: 3,
    total_hours: 7.4,
    avg_hours_per_day: 3.7,
    severity: 'High',
    activities: ['Breakdown', 'Power Failure'],
  },
];

const sampleTimeline = [
  { date: '2025-10-07', failure_hours: 1.0 },
  { date: '2025-10-08', failure_hours: 5.0 },
  { date: '2025-10-09', failure_hours: 2.4 },
  { date: '2025-10-10', failure_hours: 0.5 },
];

const sampleConfig = { minimum_events: 2, minimum_hours: 4, max_gap_hours: 6 };

describe('BreakdownStreaksPanel', () => {
  it('shows a loading state', () => {
    render(<BreakdownStreaksPanel streaks={[]} timeline={[]} config={null} loading={true} />);
    expect(screen.getByText(/loading breakdown streak data/i)).toBeInTheDocument();
  });

  it('shows an empty state when there is no failure timeline data', () => {
    render(<BreakdownStreaksPanel streaks={[]} timeline={[]} config={sampleConfig} loading={false} />);
    expect(screen.getByText(/no failure events recorded/i)).toBeInTheDocument();
  });

  it('renders detailed streak fields matching the detected streak', () => {
    render(
      <BreakdownStreaksPanel streaks={sampleStreaks} timeline={sampleTimeline} config={sampleConfig} loading={false} />,
    );
    expect(screen.getByText('Detailed Breakdown Streak')).toBeInTheDocument();
    expect(screen.getAllByText('2025-10-08').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('2025-10-09')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument(); // duration days
    expect(screen.getByText('7.4')).toBeInTheDocument();
    expect(screen.getByText('3.7')).toBeInTheDocument();
    expect(screen.getAllByText('High').length).toBeGreaterThanOrEqual(1);
  });

  it('shows a message when no streaks are detected even with timeline data', () => {
    render(
      <BreakdownStreaksPanel streaks={[]} timeline={sampleTimeline} config={sampleConfig} loading={false} />,
    );
    expect(screen.getByText(/no breakdown streaks detected/i)).toBeInTheDocument();
  });
});
