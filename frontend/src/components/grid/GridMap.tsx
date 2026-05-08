import type { GridState } from "@/hooks/useGridWebSocket";
import { fmtHour } from "@/hooks/useGridWebSocket";

interface Props { state: GridState | null }

export function GridMap({ state }: Props) {
  if (!state) return <div className="panel h-full" />;

  const solar = state.solar.total_kw;
  const load = state.grid.total_demand_kw;
  const gridImport = state.grid.net_import_kw;
  const battCharge = state.grid.battery_power_kw;
  const soc = state.battery.soc * 100;

  const importing = gridImport > 0.2;
  const exporting = gridImport < -0.2;
  const charging = battCharge > 0.2;
  const discharging = battCharge < -0.2;

  return (
    <div className="panel h-full p-4 flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="hud-label">Topology</div>
          <h3 className="font-display text-lg">Neighbourhood Grid</h3>
        </div>
        <div className="flex items-center gap-2 font-mono text-xs text-muted-foreground">
          <span className="live-dot inline-block h-2 w-2 rounded-full bg-primary" />
          {fmtHour(state.hour_of_day)} SIM
        </div>
      </div>

      <div className="relative flex-1 bg-grid rounded-sm border border-border overflow-hidden">
        <svg viewBox="0 0 600 360" className="absolute inset-0 h-full w-full">
          {/* edges */}
          <g fill="none" strokeWidth="2">
            {/* solar -> bus */}
            <line x1="120" y1="80" x2="300" y2="180" stroke="var(--solar)" opacity={solar > 0.3 ? 0.9 : 0.2}
              className={solar > 0.3 ? "flow" : ""} />
            {/* grid -> bus */}
            <line x1="480" y1="80" x2="300" y2="180" stroke="var(--grid-blue)" opacity={Math.abs(gridImport) > 0.3 ? 0.9 : 0.2}
              className={importing ? "flow" : exporting ? "flow-rev" : ""} />
            {/* bus -> battery */}
            <line x1="300" y1="180" x2="120" y2="280" stroke="var(--battery)" opacity={Math.abs(battCharge) > 0.2 ? 0.9 : 0.2}
              className={charging ? "flow" : discharging ? "flow-rev" : ""} />
            {/* bus -> houses */}
            <line x1="300" y1="180" x2="480" y2="280" stroke="var(--load)" opacity={load > 0.5 ? 0.9 : 0.3}
              className={load > 0.5 ? "flow" : ""} />
          </g>

          {/* Bus */}
          <circle cx="300" cy="180" r="18" fill="var(--surface-2)" stroke="var(--primary)" strokeWidth="2" />
          <text x="300" y="184" textAnchor="middle" fontSize="10" fill="var(--foreground)" fontFamily="monospace">BUS</text>

          {/* Solar */}
          <Node x={120} y={80} label="SOLAR" value={`${solar.toFixed(1)} kW`} color="var(--solar)" />
          {/* Grid */}
          <Node x={480} y={80} label="UTILITY" value={`${gridImport >= 0 ? "+" : ""}${gridImport.toFixed(1)} kW`} color="var(--grid-blue)" />
          {/* Battery */}
          <Node x={120} y={280} label="BATTERY" value={`${soc.toFixed(0)}% SOC`} color="var(--battery)" />
          {/* Houses */}
          <Node x={480} y={280} label={`HOUSES (${state.houses.units.length})`} value={`${load.toFixed(1)} kW`} color="var(--load)" />
        </svg>

        {/* corner legend */}
        <div className="absolute bottom-2 left-2 right-2 flex flex-wrap gap-3 text-[10px] font-mono uppercase tracking-wider text-muted-foreground">
          <Legend color="var(--solar)" label="Solar" />
          <Legend color="var(--grid-blue)" label="Grid" />
          <Legend color="var(--battery)" label="Battery" />
          <Legend color="var(--load)" label="Load" />
        </div>
      </div>
    </div>
  );
}

function Node({ x, y, label, value, color }: { x: number; y: number; label: string; value: string; color: string }) {
  return (
    <g>
      <rect x={x - 64} y={y - 26} width="128" height="52" rx="4" fill="var(--surface-2)" stroke={color} strokeWidth="1.5" />
      <text x={x} y={y - 8} textAnchor="middle" fontSize="9" fill="var(--muted-foreground)" fontFamily="monospace" letterSpacing="1.5">{label}</text>
      <text x={x} y={y + 14} textAnchor="middle" fontSize="14" fill="var(--foreground)" fontFamily="Sora" fontWeight="600">{value}</text>
    </g>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="inline-block h-2 w-2" style={{ background: color }} />
      {label}
    </span>
  );
}
