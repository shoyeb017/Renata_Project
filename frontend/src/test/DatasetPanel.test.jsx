import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import DatasetPanel from '../components/DatasetPanel';

const sampleDatasets = [
  { id: 1, name: 'shift_data.csv', source: 'default', is_active: true, row_count: 50, uploaded_at: '2026-06-24T00:00:00Z' },
  { id: 2, name: 'my_upload.csv', source: 'upload', is_active: false, row_count: 30, uploaded_at: '2026-06-23T00:00:00Z' },
];

describe('DatasetPanel', () => {
  it('shows the active dataset name and record count', () => {
    render(
      <DatasetPanel datasets={sampleDatasets} uploadState={{ status: 'idle' }} onUpload={() => {}} onActivate={() => {}} />,
    );
    expect(screen.getByText('shift_data.csv')).toBeInTheDocument();
    expect(screen.getByText(/50 records/i)).toBeInTheDocument();
  });

  it('lists previously loaded (inactive) datasets with a switch button', () => {
    render(
      <DatasetPanel datasets={sampleDatasets} uploadState={{ status: 'idle' }} onUpload={() => {}} onActivate={() => {}} />,
    );
    expect(screen.getByText('my_upload.csv')).toBeInTheDocument();
    expect(screen.getByText('Switch')).toBeInTheDocument();
  });

  it('calls onActivate with the dataset id when Switch is clicked', () => {
    const onActivate = vi.fn();
    render(
      <DatasetPanel datasets={sampleDatasets} uploadState={{ status: 'idle' }} onUpload={() => {}} onActivate={onActivate} />,
    );
    fireEvent.click(screen.getByText('Switch'));
    expect(onActivate).toHaveBeenCalledWith(2);
  });

  it('shows a success message after a completed upload', () => {
    render(
      <DatasetPanel
        datasets={sampleDatasets}
        uploadState={{ status: 'success', message: 'Loaded "new.csv" — 10 clean records.' }}
        onUpload={() => {}}
        onActivate={() => {}}
      />,
    );
    expect(screen.getByText(/loaded "new.csv"/i)).toBeInTheDocument();
  });

  it('disables the upload button while uploading', () => {
    render(
      <DatasetPanel
        datasets={sampleDatasets}
        uploadState={{ status: 'uploading', message: '' }}
        onUpload={() => {}}
        onActivate={() => {}}
      />,
    );
    expect(screen.getByText(/processing/i)).toBeDisabled();
  });
});
