import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import {
  useGridWebSocket,
  fmtHour,
  type Scenario,
} from "@/hooks/useGridWebSocket";
import { ControlSidebar } from "@/components/grid/ControlSidebar";
import { GridMap } from "@/components/grid/GridMap";
import { EnergyChart } from "@/components/grid/EnergyChart";
import { BatteryGauge } from "@/components/grid/BatteryGauge";
import { PriceChart } from "@/components/grid/PriceChart";
import { ActionLog } from "@/components/grid/ActionLog";
import { StatsPanel } from "@/components/grid/StatsPanel";
import { HousesGrid } from "@/components/grid/HousesGrid";

export const Route = createFileRoute("/")(({
  head: () => ({
    meta: [
      { title: "NeuroGrid — Smart Neighbourhood Power Grid" },
      {
        name: "description",
        content:
          "Live simulation console for an RL-optimized smart neighbourhood power grid: solar, battery, EV chargers, and AI agent decisions in real time.",
      },
      { property: "og:title", content: "NeuroGrid — Smart Grid Console" },
      {
        property: "og:description",
        content:
          "Real-time simulation of a smart neighbourhood grid with reinforcement learning energy optimization.",
      },
    ],
  }),
  component: Index,
} as any));

function Index() {
  const {
    connected,
    paused,
    currentState,
    history,
    actionLog,
    setScenario,
    injectEvent,
    pauseSimulation,
    resumeSimulation,
    resetSimulation,
  } = useGridWebSocket();

  const [activeScenario, setActiveScenario] = useState<Scenario>("baseline");

  const handleScenario = (s: Scenario) => {
    setActiveScenario(s);
    setScenario(s);
  };

  const state = currentState;
  const blackout = state?.grid?.blackout;

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      {/* Blackout Alert */}
      {blackout && (
        <div
          className="w-full text-center py-2 font-mono text-sm font-bold tracking-widest"
          style={{ background: "var(--danger)", color: "#fff" }}
        >
          ⚡ BLACKOUT — Demand exceeds supply capacity!
        </div>
      )}

      <div className="flex flex-1 min-h-0">
        <ControlSidebar
          scenario={activeScenario}
          setScenario={handleScenario}
          connected={connected}
          paused={paused}
          pauseSimulation={pauseSimulation}
          resumeSimulation={resumeSimulation}
          injectEvent={injectEvent}
          resetSimulation={resetSimulation}
        />

        <main className="flex-1 flex flex-col min-w-0">
          {/* Header */}
          <header className="h-14 border-b border-border flex items-center justify-between px-5 bg-surface shrink-0">
            <div className="flex items-center gap-4">
              <h1 className="font-display text-base">
                <span className="text-muted-foreground">NeuroGrid</span> / Live Console
              </h1>
              <span className="font-mono text-[11px] text-muted-foreground hidden md:block">
                {import.meta.env.VITE_WS_URL?.replace("wss://", "WS://") || "WS://localhost:8000"} · LIVE
              </span>
            </div>
            <div className="flex items-center gap-5 font-mono text-[11px]">
              <ConnDot connected={connected} />
              <Stat
                label="CLOCK"
                value={state ? fmtHour(state.hour_of_day) : "--:--"}
              />
              <Stat
                label="SOLAR"
                value={state ? `${(state.solar.total_kw).toFixed(1)} kW` : "—"}
                color="var(--solar)"
              />
              <Stat
                label="LOAD"
                value={
                  state ? `${(state.grid.total_demand_kw).toFixed(1)} kW` : "—"
                }
                color="var(--load)"
              />
              <Stat
                label="GRID"
                value={
                  state
                    ? `${state.grid.net_import_kw >= 0 ? "+" : ""}${state.grid.net_import_kw.toFixed(1)} kW`
                    : "—"
                }
                color="var(--grid-blue)"
              />
              <Stat
                label="SOC"
                value={
                  state ? `${(state.battery.soc * 100).toFixed(0)}%` : "—"
                }
                color="var(--battery)"
              />
            </div>
          </header>

          {/* Dashboard grid */}
          <div className="flex-1 p-4 grid grid-cols-12 grid-rows-[auto_1fr_auto_auto] gap-4 overflow-y-auto">
            {/* Stats row */}
            <div className="col-span-12">
              <StatsPanel state={state} history={history} />
            </div>

            {/* Grid map + Battery/Price */}
            <div className="col-span-12 lg:col-span-7 min-h-[380px]">
              <GridMap state={state} />
            </div>
            <div className="col-span-12 lg:col-span-5 grid grid-rows-2 gap-4 min-h-[380px]">
              <BatteryGauge
                soc={state ? state.battery.soc * 100 : 0}
                battKw={state?.grid?.battery_power_kw ?? 0}
                energyKwh={state?.battery?.energy_kwh ?? 0}
                capacityKwh={state?.battery?.capacity_kwh ?? 50}
              />
              <PriceChart history={history} currentHour={state?.hour_of_day} />
            </div>

            {/* Energy chart + Action log */}
            <div className="col-span-12 lg:col-span-7 min-h-[260px]">
              <EnergyChart history={history} />
            </div>
            <div className="col-span-12 lg:col-span-5 min-h-[260px]">
              <ActionLog
                actions={actionLog}
                scenario={activeScenario}
              />
            </div>

            {/* Houses grid */}
            <div className="col-span-12">
              <HousesGrid state={state} />
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

function ConnDot({ connected }: { connected: boolean }) {
  return (
    <span className="flex items-center gap-1.5 font-mono text-[11px]">
      <span
        className={`h-1.5 w-1.5 rounded-full ${connected ? "live-dot bg-[var(--battery)]" : "bg-[var(--danger)]"}`}
      />
      <span style={{ color: connected ? "var(--battery)" : "var(--danger)" }}>
        {connected ? "LIVE" : "OFFLINE"}
      </span>
    </span>
  );
}

function Stat({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <span className="flex items-baseline gap-1.5">
      <span className="hud-label">{label}</span>
      <span className="stat-num text-sm" style={{ color }}>
        {value}
      </span>
    </span>
  );
}
