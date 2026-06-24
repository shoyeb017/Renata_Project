import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import InsightPanel from '../components/InsightPanel';

const sampleInsights = [
  {
    title: 'Operational Efficiency Status',
    metric: '77.1%',
    text: 'Current operational efficiency is 77.13% (good). Productive hours: 99.5 / 129.0 total hours.',
    action: 'Focus on reducing minor breakdowns and optimizing shift schedules.',
    severity: 'Medium',
  },
  {
    title: 'Breakdown Risk Assessment',
    metric: '18.0h',
    text: 'Active breakdown streak: 1 days with 18.0 hours total impact.',
    action: "Investigate 'Breakdown' incidents and implement targeted prevention measures.",
    severity: 'Critical',
  },
];

describe('InsightPanel', () => {
  it('shows an empty state when there are no insights', () => {
    render(<InsightPanel insights={[]} />);
    expect(screen.getByText(/no insights available/i)).toBeInTheDocument();
  });

  it('renders title, metric, text, action, and severity for each insight', () => {
    render(<InsightPanel insights={sampleInsights} />);
    expect(screen.getByText('Operational Efficiency Status')).toBeInTheDocument();
    expect(screen.getByText('77.1%')).toBeInTheDocument();
    expect(screen.getByText(/focus on reducing minor breakdowns/i)).toBeInTheDocument();
    expect(screen.getByText('Critical')).toBeInTheDocument();
  });

  it('renders one card per insight', () => {
    const { container } = render(<InsightPanel insights={sampleInsights} />);
    expect(container.querySelectorAll('.insight-card').length).toBe(sampleInsights.length);
  });
});
