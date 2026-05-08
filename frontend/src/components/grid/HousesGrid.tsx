import type { GridState } from "@/hooks/useGridWebSocket";

interface Props {
  state: GridState | null;
}

export function HousesGrid({ state }: Props) {
  if (!state) return null;

  const houses = state.houses?.units ?? [];
  const evs = state.ev_chargers?.units ?? [];

  // Map EV load by index for display
  const evByIndex = evs.reduce<Record<number, (typeof evs)[0]>>((acc, ev, i) => {
    acc[i] = ev;
    return acc;
  }, {});

  return (
    <div className="panel p-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="hud-label">Endpoints · MQTT grid/house/*</div>
          <h3 className="font-display text-lg">Houses</h3>
        </div>
        <div className="flex items-center gap-3 font-mono text-[11px] text-muted-foreground">
          <span>
            {evs.filter((e) => e.connected).length}/{evs.length} EV connected
          </span>
          <span>
            {houses.length} units
          </span>
        </div>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
        {houses.map((h, i) => {
          const ev = evByIndex[i];
          const evLoad = ev?.connected ? (ev.load_kw ?? 0) : 0;
          const total = (h.load_kw ?? 0) + evLoad;
          const intensity = Math.min(1, total / 7);
          return (
            <div key={h.id ?? i} className="panel-2 p-3 relative overflow-hidden">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] text-muted-foreground">
                  {h.name ?? h.id ?? `H-0${i + 1}`}
                </span>
                <span
                  className="h-1.5 w-1.5 rounded-full live-dot"
                  style={{
                    background: `color-mix(in oklab, var(--primary) ${intensity * 100}%, var(--muted))`,
                  }}
                />
              </div>
              <div className="stat-num text-xl mt-1">
                {total.toFixed(1)}
                <span className="text-xs text-muted-foreground"> kW</span>
              </div>
              <div className="font-mono text-[10px] text-muted-foreground mt-1">
                load {(h.load_kw ?? 0).toFixed(1)}{" "}
                {evLoad > 0 && (
                  <span style={{ color: "var(--primary)" }}>
                    · EV {evLoad.toFixed(1)}
                  </span>
                )}
              </div>
              <div
                className="absolute bottom-0 left-0 h-[2px] bg-primary"
                style={{ width: `${intensity * 100}%` }}
              />
            </div>
          );
        })}
      </div>

      {/* EV Chargers row */}
      {evs.length > 0 && (
        <div className="mt-3">
          <div className="hud-label mb-2">EV Chargers · MQTT grid/ev/*</div>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
            {evs.map((ev, i) => (
              <div
                key={ev.id ?? i}
                className="panel-2 p-2 flex items-center gap-2"
              >
                <span className="text-lg">{ev.connected ? "🔌" : "🚗"}</span>
                <div>
                  <div className="font-mono text-[10px] text-muted-foreground">
                    EV-{i + 1}
                  </div>
                  <div className="stat-num text-sm">
                    {ev.connected
                      ? `${(ev.load_kw ?? 0).toFixed(1)} kW`
                      : "idle"}
                  </div>
                  {ev.battery_soc !== undefined && (
                    <div className="font-mono text-[10px]" style={{ color: "var(--battery)" }}>
                      {(ev.battery_soc * 100).toFixed(0)}% SOC
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
