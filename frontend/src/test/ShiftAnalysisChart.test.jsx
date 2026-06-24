import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ShiftAnalysisChart from '../components/ShiftAnalysisChart';

const sampleBlocks = [
  {
    id: 1,
    date: '2025-10-01',
    activity_name: 'Training',
    category: 'Productive',
    color: '#2E8B7E',
    productive: true,
    start_label: '07:00',
    end_label: '09:00',
    start_hour: 7,
    end_hour: 9,
    duration_hours: 2,
  },
];

describe('ShiftAnalysisChart', () => {
  it('shows an empty state when there are no blocks', () => {
    render(<ShiftAnalysisChart blocks={[]} />);
    expect(screen.getByText(/no shift records match/i)).toBeInTheDocument();
  });

  it('renders required Y-axis time labels including next-day hours', () => {
    render(<ShiftAnalysisChart blocks={sampleBlocks} />);
    expect(screen.getByText('12 AM')).toBeInTheDocument();
    expect(screen.getByText('Next 12 AM')).toBeInTheDocument();
    expect(screen.getByText('Next 12 PM')).toBeInTheDocument();
  });

  it('renders one SVG rect per shift block', () => {
    const { container } = render(<ShiftAnalysisChart blocks={sampleBlocks} />);
    const rects = container.querySelectorAll('rect');
    expect(rects.length).toBe(sampleBlocks.length);
  });
});
