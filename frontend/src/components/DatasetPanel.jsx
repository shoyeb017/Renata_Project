import { useRef } from "react";
import "./DatasetPanel.css";

function formatTimestamp(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export default function DatasetPanel({ datasets, uploadState, onUpload, onActivate }) {
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) onUpload(file);
    e.target.value = "";
  };

  const activeDataset = datasets.find((d) => d.is_active);

  return (
    <div className="dataset-panel">
      <div className="dataset-panel__header">
        <span className="dataset-panel__title">Dataset</span>
      </div>

      <div className="dataset-panel__active">
        <span className="dataset-panel__active-dot" aria-hidden="true" />
        <div className="dataset-panel__active-info">
          <span className="dataset-panel__active-name">{activeDataset?.name ?? "—"}</span>
          <span className="dataset-panel__active-meta mono">
            {activeDataset?.row_count ?? 0} records
            {activeDataset?.source === "default" ? " · bundled default" : " · uploaded"}
          </span>
        </div>
      </div>

      <button
        type="button"
        className="dataset-panel__upload-btn"
        onClick={() => fileInputRef.current?.click()}
        disabled={uploadState.status === "uploading"}
      >
        {uploadState.status === "uploading" ? "Processing…" : "Upload new CSV"}
      </button>
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv"
        onChange={handleFileChange}
        className="dataset-panel__file-input"
      />

      {uploadState.status === "success" && (
        <p className="dataset-panel__status dataset-panel__status--success">{uploadState.message}</p>
      )}
      {uploadState.status === "error" && (
        <p className="dataset-panel__status dataset-panel__status--error">{uploadState.message}</p>
      )}

      {datasets.length > 1 && (
        <div className="dataset-panel__history">
          <span className="dataset-panel__history-label">Previously loaded</span>
          <ul className="dataset-panel__history-list">
            {datasets
              .filter((d) => !d.is_active)
              .map((d) => (
                <li key={d.id} className="dataset-panel__history-item">
                  <div className="dataset-panel__history-info">
                    <span className="dataset-panel__history-name">{d.name}</span>
                    <span className="dataset-panel__history-meta mono">
                      {d.row_count} rows · {formatTimestamp(d.uploaded_at)}
                    </span>
                  </div>
                  <button
                    type="button"
                    className="dataset-panel__activate-btn"
                    onClick={() => onActivate(d.id)}
                  >
                    Switch
                  </button>
                </li>
              ))}
          </ul>
        </div>
      )}
    </div>
  );
}
