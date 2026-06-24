import "./ActivityLegend.css";

/**
 * Legend derived entirely from the activity_configs returned by
 * /api/filter-options. New activities (including auto-registered/
 * "Uncategorized" ones) appear automatically with no code change.
 */
export default function ActivityLegend({ activityConfigs }) {
  if (!activityConfigs?.length) return null;

  const grouped = activityConfigs.reduce((acc, cfg) => {
    acc[cfg.category] = acc[cfg.category] || [];
    acc[cfg.category].push(cfg);
    return acc;
  }, {});

  return (
    <div className="legend">
      {Object.entries(grouped).map(([category, items]) => (
        <div className="legend__group" key={category}>
          <span className="legend__group-label">{category}</span>
          <div className="legend__items">
            {items.map((cfg) => (
              <span className="legend__item" key={cfg.id}>
                <span className="legend__swatch" style={{ background: cfg.display_color }} />
                {cfg.activity_name}
                {cfg.is_auto_registered && <span className="legend__auto-badge" title="Auto-registered: not yet manually classified">auto</span>}
              </span>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
