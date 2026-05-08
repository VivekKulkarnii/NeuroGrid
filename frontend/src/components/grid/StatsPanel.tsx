import type { GridState } from "@/hooks/useGridWebSocket";

interface Props {
  state: GridState | null;
  history: GridState[];
}

export function StatsPanel({ state, history }: Props) {
  if (!state) return null;

  const metrics = state.metrics ?? {};
  const grid = state.grid ?? {};
  const battery = state.battery ?? {};
  const price = state.price ?? {};

  // Avg solar over last 50 ticks
  const avgSolar =
    history.length > 10
      ? history.slice(-50).reduce((s, h) => s + (h.solar?.total_kw ?? 0), 0) /
        Math.min(50, history.length)
      : state.solar?.total_kw ?? 0;

  const avgDemand =
    history.length > 10
      ? history
          .slice(-50)
          .reduce((s, h) => s + (h.grid?.total_demand_kw ?? 0), 0) /
        Math.min(50, history.length)
      : grid.total_demand_kw ?? 0;

  const selfSufficiency =
    avgDemand > 0
      ? Math.min(100, (avgSolar / avgDemand) * 100).toFixed(0)
      : "0";

  const tierColor =
    price.tier === "peak"
      ? "var(--danger)"
      : price.tier === "shoulder"
        ? "var(--solar)"
        : "var(--battery)";

  const items = [
    {
      label: "Total Cost",
      value: `$${(metrics.total_cost ?? 0).toFixed(4)}`,
      accent:
        (metrics.total_cost ?? 0) > 5
          ? "var(--danger)"
          : (metrics.total_cost ?? 0) > 2
            ? "var(--solar)"
            : "var(--battery)",
    },
    {
      label: "Blackouts",
      value: String(metrics.blackout_count ?? 0),
      accent:
        (metrics.blackout_count ?? 0) > 0 ? "var(--danger)" : "var(--battery)",
    },
    {
      label: "Price",
      value: `$${(price.import_rate ?? 0).toFixed(4)}/kWh`,
      accent: tierColor,
    },
    {
      label: "Net Import",
      value: `${(grid.net_import_kw ?? 0).toFixed(2)} kW`,
      accent:
        (grid.net_import_kw ?? 0) > 15
          ? "var(--danger)"
          : (grid.net_import_kw ?? 0) > 5
            ? "var(--solar)"
            : "var(--battery)",
    },
    {
      label: "Self-Sufficiency",
      value: `${selfSufficiency}%`,
      accent:
        Number(selfSufficiency) > 70
          ? "var(--battery)"
          : Number(selfSufficiency) > 40
            ? "var(--solar)"
            : "var(--danger)",
    },
    {
      label: "Battery SOC",
      value: `${((battery.soc ?? 0) * 100).toFixed(1)}%`,
      accent:
        (battery.soc ?? 0) > 0.5
          ? "var(--battery)"
          : (battery.soc ?? 0) > 0.2
            ? "var(--solar)"
            : "var(--danger)",
    },
  ];

  return (
    <div className="panel p-4 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
      {items.map((it) => (
        <div key={it.label} className="panel-2 p-3">
          <div className="hud-label">{it.label}</div>
          <div
            className="stat-num text-2xl mt-1"
            style={{ color: it.accent }}
          >
            {it.value}
          </div>
        </div>
      ))}
    </div>
  );
}
