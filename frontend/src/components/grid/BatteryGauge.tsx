interface Props {
  soc: number;       // 0–100
  battKw: number;    // + charging / - discharging
  energyKwh?: number;
  capacityKwh?: number;
}

export function BatteryGauge({ soc, battKw, energyKwh = 0, capacityKwh = 50 }: Props) {
  const charging = battKw > 0.1;
  const discharging = battKw < -0.1;
  const status = charging ? "CHARGING" : discharging ? "DISCHARGING" : "IDLE";
  const tone = charging
    ? "var(--battery)"
    : discharging
      ? "var(--primary)"
      : "var(--muted-foreground)";

  return (
    <div className="panel p-4 h-full flex flex-col">
      <div className="flex items-center justify-between">
        <div>
          <div className="hud-label">Battery bank</div>
          <h3 className="font-display text-lg">{capacityKwh} kWh</h3>
        </div>
        <span
          className="font-mono text-[10px] tracking-widest px-2 py-1 border"
          style={{ color: tone, borderColor: tone }}
        >
          {status}
        </span>
      </div>

      <div className="flex-1 flex items-center justify-center my-3">
        <div className="relative w-full max-w-[220px] aspect-[2/1]">
          <svg viewBox="0 0 200 100" className="w-full h-full">
            <path
              d="M10 90 A 90 90 0 0 1 190 90"
              fill="none"
              stroke="var(--surface-2)"
              strokeWidth="14"
              strokeLinecap="round"
            />
            <path
              d="M10 90 A 90 90 0 0 1 190 90"
              fill="none"
              stroke="var(--battery)"
              strokeWidth="14"
              strokeLinecap="round"
              strokeDasharray={`${(soc / 100) * 283} 283`}
            />
          </svg>
          <div className="absolute inset-0 flex flex-col items-center justify-end pb-1">
            <div className="stat-num text-4xl">
              {soc.toFixed(0)}
              <span className="text-xl text-muted-foreground">%</span>
            </div>
            <div className="hud-label">State of charge</div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2 text-center">
        <div className="panel-2 py-2">
          <div className="hud-label">Power</div>
          <div className="stat-num text-base" style={{ color: tone }}>
            {battKw >= 0 ? "+" : ""}
            {battKw.toFixed(1)} kW
          </div>
        </div>
        <div className="panel-2 py-2">
          <div className="hud-label">Stored</div>
          <div className="stat-num text-base">
            {energyKwh.toFixed(1)} kWh
          </div>
        </div>
      </div>
    </div>
  );
}
