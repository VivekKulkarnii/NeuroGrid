import { useMemo } from "react";
import type { GridState } from "@/hooks/useGridWebSocket";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

interface Props {
  history: GridState[];
}

const CustomTooltip = ({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: any[];
  label?: any;
}) => {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        background: "rgba(17, 24, 39, 0.95)",
        border: "1px solid rgba(99, 102, 241, 0.3)",
        borderRadius: "10px",
        padding: "12px 16px",
        fontSize: "12px",
        fontFamily: "'JetBrains Mono', monospace",
        boxShadow: "0 8px 30px rgba(0,0,0,0.5)",
        backdropFilter: "blur(10px)",
      }}
    >
      <p style={{ color: "#94a3b8", marginBottom: 6 }}>
        Hour: {typeof label === "number" ? label.toFixed(1) : label}
      </p>
      {payload.map((entry, i) => (
        <p key={i} style={{ color: entry.color, margin: "3px 0" }}>
          {entry.name}: {typeof entry.value === "number" ? entry.value.toFixed(2) : entry.value} kW
        </p>
      ))}
    </div>
  );
};

export function EnergyChart({ history }: Props) {
  const data = useMemo(() => {
    if (!history?.length) return [];
    return history.slice(-150).map((s) => ({
      hour: s.hour_of_day,
      solar: s.solar?.total_kw ?? 0,
      demand: s.grid?.total_demand_kw ?? 0,
      netImport: s.grid?.net_import_kw ?? 0,
    }));
  }, [history]);

  if (data.length < 2) {
    return (
      <div className="panel h-full p-4">
        <div className="hud-label mb-1">Energy flow</div>
        <div className="text-muted-foreground text-sm">Warming up…</div>
      </div>
    );
  }

  return (
    <div className="panel p-4 h-full flex flex-col">
      <div className="flex items-end justify-between mb-2">
        <div>
          <div className="hud-label">Power flow · real-time</div>
          <h3 className="font-display text-lg">Energy Telemetry</h3>
        </div>
      </div>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
            <defs>
              <linearGradient id="solarGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#fbbf24" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#fbbf24" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="demandGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#a78bfa" stopOpacity={0.4} />
                <stop offset="95%" stopColor="#a78bfa" stopOpacity={0.0} />
              </linearGradient>
              <linearGradient id="importGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#f87171" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#f87171" stopOpacity={0.0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
            <XAxis
              dataKey="hour"
              tick={{ fill: "#64748b", fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
              tickFormatter={(v) => `${Math.floor(v)}h`}
              stroke="rgba(255,255,255,0.1)"
            />
            <YAxis
              tick={{ fill: "#64748b", fontSize: 11, fontFamily: "'JetBrains Mono', monospace" }}
              stroke="rgba(255,255,255,0.1)"
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ fontSize: "12px", fontFamily: "'Inter', sans-serif" }} />
            <Area
              type="monotone"
              dataKey="solar"
              name="Solar"
              stroke="#fbbf24"
              fill="url(#solarGrad)"
              strokeWidth={2}
              dot={false}
            />
            <Area
              type="monotone"
              dataKey="demand"
              name="Demand"
              stroke="#a78bfa"
              fill="url(#demandGrad)"
              strokeWidth={2}
              dot={false}
            />
            <Area
              type="monotone"
              dataKey="netImport"
              name="Grid Import"
              stroke="#f87171"
              fill="url(#importGrad)"
              strokeWidth={1.5}
              dot={false}
              strokeDasharray="4 4"
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
