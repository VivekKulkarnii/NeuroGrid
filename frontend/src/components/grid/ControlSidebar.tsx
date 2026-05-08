import type { Scenario } from "@/hooks/useGridWebSocket";
import { Cloud, Zap, DollarSign, Sun, RefreshCw, Gauge, Cpu, Activity, Pause, Play } from "lucide-react";

interface Props {
  scenario: Scenario;
  setScenario: (s: Scenario) => void;
  connected: boolean;
  paused: boolean;
  pauseSimulation: () => void;
  resumeSimulation: () => void;
  injectEvent: (eventType: string, intensity?: number) => void;
  resetSimulation: () => void;
}

export function ControlSidebar({ scenario, setScenario, connected, paused, pauseSimulation, resumeSimulation, injectEvent, resetSimulation }: Props) {
  const scenarios: { id: Scenario; name: string; desc: string; icon: React.ReactNode }[] = [
    { id: "baseline", name: "Baseline", desc: "Rule-based controller", icon: <Gauge className="h-4 w-4" /> },
    { id: "ai", name: "AI Agent", desc: "RL optimizer (PPO)", icon: <Cpu className="h-4 w-4" /> },
    { id: "stress", name: "Stress Test", desc: "AI under disturbance", icon: <Activity className="h-4 w-4" /> },
  ];

  return (
    <aside className="w-72 shrink-0 bg-sidebar border-r border-sidebar-border flex flex-col">
      {/* Brand */}
      <div className="p-5 border-b border-sidebar-border">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 grid place-items-center bg-primary text-primary-foreground font-display font-bold">
            M
          </div>
          <div>
            <div className="font-display text-sm leading-tight">MC-IOT</div>
            <div className="hud-label leading-tight">Smart Grid Console</div>
          </div>
        </div>
      </div>

      <div className="p-4 space-y-4 flex-1 overflow-y-auto">
        {/* Scenario selector */}
        <section>
          <div className="hud-label mb-2">Scenario</div>
          <div className="space-y-1.5">
            {scenarios.map((s) => {
              const active = scenario === s.id;
              return (
                <button
                  key={s.id}
                  onClick={() => setScenario(s.id)}
                  className={`w-full text-left p-3 border transition-colors flex gap-3 items-start ${
                    active
                      ? "border-primary bg-primary/10"
                      : "border-sidebar-border hover:bg-sidebar-accent"
                  }`}
                >
                  <span className={active ? "text-primary mt-0.5" : "text-muted-foreground mt-0.5"}>
                    {s.icon}
                  </span>
                  <span>
                    <span className="block font-display text-sm">{s.name}</span>
                    <span className="block text-[11px] text-muted-foreground">{s.desc}</span>
                  </span>
                </button>
              );
            })}
          </div>
        </section>

        {/* Stress injectors */}
        <section>
          <div className="hud-label mb-2">Stress Injectors</div>
          <div className="grid grid-cols-2 gap-1.5">
            <button
              onClick={() => injectEvent("cloud_cover", 1.0)}
              className="p-3 border border-sidebar-border hover:bg-sidebar-accent flex flex-col items-center gap-1"
            >
              <Cloud className="h-4 w-4 text-[var(--solar)]" />
              <span className="font-mono text-[10px] uppercase tracking-widest">Cloud</span>
            </button>
            <button
              onClick={() => injectEvent("ev_surge", 1.0)}
              className="p-3 border border-sidebar-border hover:bg-sidebar-accent flex flex-col items-center gap-1"
            >
              <Zap className="h-4 w-4 text-[var(--primary)]" />
              <span className="font-mono text-[10px] uppercase tracking-widest">EV Surge</span>
            </button>
            <button
              onClick={() => injectEvent("price_spike", 1.0)}
              className="p-3 border border-sidebar-border hover:bg-sidebar-accent flex flex-col items-center gap-1"
            >
              <DollarSign className="h-4 w-4 text-[var(--danger)]" />
              <span className="font-mono text-[10px] uppercase tracking-widest">Price Spike</span>
            </button>
            <button
              onClick={() => injectEvent("cloud_cover", 0.0)}
              className="p-3 border border-sidebar-border hover:bg-sidebar-accent flex flex-col items-center gap-1"
            >
              <Sun className="h-4 w-4 text-[var(--solar)]" />
              <span className="font-mono text-[10px] uppercase tracking-widest">Clear Sky</span>
            </button>
          </div>
        </section>

        {/* Simulation control */}
        <section>
          <div className="hud-label mb-2">Simulation</div>
          <button
            onClick={paused ? resumeSimulation : pauseSimulation}
            className={`w-full p-3 border transition-colors flex items-center gap-2 font-mono text-xs uppercase tracking-widest ${
              paused
                ? "border-[var(--battery)] text-[var(--battery)] bg-[var(--battery)]/10 hover:bg-[var(--battery)]/20"
                : "border-sidebar-border hover:bg-sidebar-accent"
            }`}
          >
            {paused ? <Play className="h-4 w-4" /> : <Pause className="h-4 w-4" />}
            {paused ? "Resume" : "Pause"}
          </button>
          <button
            onClick={resetSimulation}
            className="w-full mt-1.5 p-3 border border-sidebar-border hover:bg-sidebar-accent flex items-center gap-2 font-mono text-xs uppercase tracking-widest"
          >
            <RefreshCw className="h-4 w-4" />
            Reset Simulation
          </button>
        </section>

        {/* MQTT topics reference */}
        <section className="panel-2 p-3">
          <div className="hud-label mb-1">MQTT Topics</div>
          <ul className="font-mono text-[11px] text-muted-foreground space-y-0.5">
            <li>grid/solar</li>
            <li>grid/house/+</li>
            <li>grid/ev/+</li>
            <li>grid/battery</li>
            <li>grid/price</li>
          </ul>
        </section>
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-sidebar-border font-mono text-[10px] text-muted-foreground flex items-center justify-between">
        <span>v1.0 · live backend</span>
        <span className="flex items-center gap-1">
          <span
            className={`h-1.5 w-1.5 rounded-full ${connected ? "live-dot bg-[var(--battery)]" : "bg-[var(--danger)]"}`}
          />
          {connected ? "ONLINE" : "OFFLINE"}
        </span>
      </div>
    </aside>
  );
}
