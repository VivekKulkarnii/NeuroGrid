import { useMemo } from "react";
import type { GridState } from "@/hooks/useGridWebSocket";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

interface Props {
  history: GridState[];
  currentHour?: number;
}

const PriceTooltip = ({
  active,
  payload,
}: {
  active?: boolean;
  payload?: any[];
}) => {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return (
    <div
      style={{
        background: "rgba(17, 24, 39, 0.95)",
        border: "1px solid rgba(34, 211, 238, 0.3)",
        borderRadius: "10px",
        padding: "10px 14px",
        fontSize: "12px",
        fontFamily: "'JetBrains Mono', monospace",
      }}
    >
      <p style={{ color: "#94a3b8" }}>Hour: {d?.hour?.toFixed(1)}</p>
      <p style={{ color: "#22d3ee" }}>Price: ₹{d?.price?.toFixed(2)}/kWh</p>
      <p style={{ color: "#64748b", textTransform: "capitalize" }}>
        Tier: {d?.tier || "unknown"}
      </p>
    </div>
  );
};

export function PriceChart({ history, currentHour }: Props) {
  const data = useMemo(() => {
    if (!history?.length) return [];
    return history.slice(-150).map((s) => ({
      hour: s.hour_of_day,
      price: s.price?.import_rate ?? 0,
      tier: s.price?.tier ?? "off_peak",
    }));
  }, [history]);

  const current = data.length ? data[data.length - 1]?.price ?? 0 : 0;
  const tier =
    current >= 10.0
      ? { name: "PEAK", color: "var(--danger)" }
      : current >= 5.0
        ? { name: "MID", color: "var(--solar)" }
        : { name: "OFF-PEAK", color: "var(--battery)" };

  if (data.length < 2) {
    return (
      <div className="panel p-4 h-full">
        <div className="hud-label">Price</div>
      </div>
    );
  }

  return (
    <div className="panel p-4 h-full flex flex-col">
      <div className="flex items-start justify-between mb-2">
        <div>
          <div className="hud-label">Tariff · time of use</div>
          <div className="stat-num text-2xl">
            ₹{current.toFixed(2)}
            <span className="text-xs text-muted-foreground"> /kWh</span>
          </div>
        </div>
        <span
          className="font-mono text-[10px] tracking-widest px-2 py-1 border"
          style={{ color: tier.color, borderColor: tier.color }}
        >
          {tier.name}
        </span>
      </div>
      <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 5, right: 10, left: -10, bottom: 0 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(255,255,255,0.05)"
            />
            <XAxis
              dataKey="hour"
              tick={{
                fill: "#64748b",
                fontSize: 11,
                fontFamily: "'JetBrains Mono', monospace",
              }}
              tickFormatter={(v) => `${Math.floor(v)}h`}
              stroke="rgba(255,255,255,0.1)"
            />
            <YAxis
              tick={{ fill: "#64748b", fontSize: 11 }}
              stroke="rgba(255,255,255,0.1)"
              tickFormatter={(v) => `₹${v.toFixed(2)}`}
            />
            <Tooltip content={<PriceTooltip />} />
            <Line
              type="monotone"
              dataKey="price"
              stroke="#22d3ee"
              strokeWidth={2}
              dot={false}
            />
            {currentHour !== undefined && (
              <ReferenceLine
                x={currentHour}
                stroke="#818cf8"
                strokeDasharray="3 3"
                strokeWidth={1}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
