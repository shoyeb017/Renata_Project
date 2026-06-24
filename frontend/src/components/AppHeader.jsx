import "./AppHeader.css";

export default function AppHeader({ dateRange }) {
  return (
    <header className="app-header">
      <div className="app-header__brand">
        <span className="app-header__signal" aria-hidden="true" />
        <h1 className="app-header__title">Shift Ops Console</h1>
      </div>
      {dateRange && (
        <span className="app-header__range mono">
          {dateRange.start} — {dateRange.end}
        </span>
      )}
    </header>
  );
}
