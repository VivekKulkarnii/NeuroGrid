import { useEffect, useRef, useState, useCallback } from "react";

export type Scenario = "baseline" | "ai" | "stress";

export type House = { id: string; name: string; load: number; ev: number };
export type Action = {
  id: number;
  t: number;
  agent: "AI" | "RULE" | "SYS";
  text: string;
  tone: "info" | "good" | "warn" | "bad";
};
export type Tick = {
  t: number;            // sim seconds
  hour: number;         // 0..24 (float)
  solar: number;        // kW produced
  load: number;         // kW total houses + EVs
  battery: number;      // SOC % 0..100
  battCharge: number;   // kW into battery (+) or out (-)
  gridImport: number;   // kW from grid (negative = export)
  price: number;        // $/kWh
  cost: number;         // cumulative $
  baselineCost: number; // cumulative $ rule-based reference
  houses: House[];
};

const HOUSE_NAMES = ["H-01", "H-02", "H-03", "H-04", "H-05", "H-06"];

function solarOutput(hour: number, cloud: number) {
  // bell-curve 6..20
  if (hour < 5.5 || hour > 20.5) return 0;
  const x = (hour - 13) / 4.2;
  const peak = 28 * Math.exp(-x * x); // ~28 kW peak
  return Math.max(0, peak * (1 - cloud));
}

function houseLoad(hour: number, seed: number) {
  // morning + evening peaks
  const m = Math.exp(-Math.pow((hour - 7.5) / 1.4, 2)) * 2.4;
  const e = Math.exp(-Math.pow((hour - 19) / 1.6, 2)) * 3.6;
  const base = 0.4 + 0.3 * Math.sin(seed * 13 + hour);
  return Math.max(0.2, base + m + e + (Math.random() - 0.5) * 0.25);
}

function priceAt(hour: number) {
  // time-of-use $/kWh
  if (hour >= 17 && hour < 21) return 0.42; // peak
  if (hour >= 7 && hour < 17) return 0.22;  // mid
  return 0.11;                               // off-peak
}

export function useGridSimulation() {
  const [scenario, setScenario] = useState<Scenario>("ai");
  const [running, setRunning] = useState(true);
  const [speed, setSpeed] = useState(60); // sim minutes per real second
  const [tick, setTick] = useState<Tick | null>(null);
  const [history, setHistory] = useState<Tick[]>([]);
  const [actions, setActions] = useState<Action[]>([]);

  const stateRef = useRef({
    simSeconds: 6 * 3600, // start at 6am
    soc: 55,
    cost: 0,
    baselineCost: 0,
    cloud: 0.05,
    evDemand: 1,
    actionId: 1,
  });

  const pushAction = useCallback((a: Omit<Action, "id" | "t">) => {
    setActions((prev) => {
      const next: Action = { ...a, id: stateRef.current.actionId++, t: stateRef.current.simSeconds };
      return [next, ...prev].slice(0, 60);
    });
  }, []);

  const triggerStress = useCallback((kind: "cloud" | "ev") => {
    if (kind === "cloud") {
      stateRef.current.cloud = 0.75;
      pushAction({ agent: "SYS", text: "Stress: heavy cloud cover injected (-75% solar)", tone: "warn" });
      setTimeout(() => { stateRef.current.cloud = 0.05; }, 8000);
    } else {
      stateRef.current.evDemand = 4;
      pushAction({ agent: "SYS", text: "Stress: EV surge — 4× charging demand", tone: "warn" });
      setTimeout(() => { stateRef.current.evDemand = 1; }, 8000);
    }
  }, [pushAction]);

  useEffect(() => {
    if (!running) return;
    const interval = 250; // ms
    const id = setInterval(() => {
      const dtSimMin = (speed * interval) / 1000; // sim minutes per tick
      const dtH = dtSimMin / 60;
      const s = stateRef.current;
      s.simSeconds += dtSimMin * 60;
      const hour = (s.simSeconds / 3600) % 24;

      const solar = solarOutput(hour, s.cloud);
      const houses: House[] = HOUSE_NAMES.map((name, i) => {
        const load = houseLoad(hour, i + 1);
        const evActive = (hour >= 18 || hour < 7) && (i % 2 === 0);
        const ev = evActive ? 3.2 * s.evDemand * (0.7 + 0.3 * Math.random()) : 0;
        return { id: name, name, load, ev };
      });
      const totalLoad = houses.reduce((a, h) => a + h.load + h.ev, 0);
      const price = priceAt(hour);

      // ---- Controllers ----
      // baseline: simple thresholds (always run for comparison cost)
      const baselineAction = baselineControl(s.soc, solar, totalLoad);
      // AI: price + forecast aware
      const aiAction = aiControl(s.soc, solar, totalLoad, price, hour);

      const useAi = scenario !== "baseline";
      const battKw = useAi ? aiAction.battKw : baselineAction.battKw;

      // apply battery (positive = charging)
      const battEnergy = battKw * dtH; // kWh
      const battCapacity = 40; // kWh
      let newSoc = s.soc + (battEnergy / battCapacity) * 100;
      newSoc = Math.max(5, Math.min(98, newSoc));
      const actualBattKw = ((newSoc - s.soc) / 100) * battCapacity / dtH;
      s.soc = newSoc;

      const net = totalLoad + actualBattKw - solar; // grid import
      const gridImport = net;
      s.cost += Math.max(0, gridImport) * dtH * price - Math.max(0, -gridImport) * dtH * price * 0.4;

      // baseline cost (parallel calc)
      const bBattKw = baselineAction.battKw;
      const bGrid = totalLoad + bBattKw - solar;
      s.baselineCost += Math.max(0, bGrid) * dtH * price - Math.max(0, -bGrid) * dtH * price * 0.4;

      // log AI decisions occasionally
      if (useAi && aiAction.note && Math.random() < 0.18) {
        pushAction({ agent: "AI", text: aiAction.note, tone: aiAction.tone });
      } else if (!useAi && baselineAction.note && Math.random() < 0.08) {
        pushAction({ agent: "RULE", text: baselineAction.note, tone: "info" });
      }

      const newTick: Tick = {
        t: s.simSeconds,
        hour,
        solar,
        load: totalLoad,
        battery: s.soc,
        battCharge: actualBattKw,
        gridImport,
        price,
        cost: s.cost,
        baselineCost: s.baselineCost,
        houses,
      };
      setTick(newTick);
      setHistory((h) => {
        const next = [...h, newTick];
        return next.length > 240 ? next.slice(next.length - 240) : next;
      });
    }, interval);
    return () => clearInterval(id);
  }, [running, speed, scenario, pushAction]);

  return {
    tick, history, actions, scenario, setScenario,
    running, setRunning, speed, setSpeed, triggerStress,
  };
}

function baselineControl(soc: number, solar: number, load: number) {
  let battKw = 0;
  let note = "";
  const tone: Action["tone"] = "info";
  const surplus = solar - load;
  if (surplus > 0.5 && soc < 95) { battKw = Math.min(8, surplus); note = "Charging battery from solar surplus"; }
  else if (surplus < -0.5 && soc > 20) { battKw = -Math.min(8, -surplus); note = "Discharging battery to cover load"; }
  return { battKw, note, tone };
}

function aiControl(soc: number, solar: number, load: number, price: number, hour: number) {
  let battKw = 0;
  let note = "";
  let tone: Action["tone"] = "info";
  const surplus = solar - load;
  const peakHours = hour >= 17 && hour < 21;
  const offPeak = price <= 0.12;

  if (peakHours && soc > 25) {
    battKw = -Math.min(10, Math.max(2, load * 0.7));
    note = `Peak price $${price.toFixed(2)} — discharging ${Math.abs(battKw).toFixed(1)} kW`;
    tone = "good";
  } else if (offPeak && soc < 80) {
    battKw = Math.min(8, 6);
    note = `Off-peak — charging battery at $${price.toFixed(2)}/kWh`;
    tone = "good";
  } else if (surplus > 0.3 && soc < 96) {
    battKw = Math.min(10, surplus);
    note = `Storing ${battKw.toFixed(1)} kW solar surplus`;
    tone = "good";
  } else if (surplus < -0.3 && soc > 30) {
    battKw = -Math.min(8, -surplus);
    note = `Covering deficit ${(-surplus).toFixed(1)} kW from battery`;
    tone = "info";
  }
  if (soc < 15) { battKw = Math.max(battKw, 2); note = "SOC critical — forcing charge"; tone = "warn"; }
  return { battKw, note, tone };
}

export function fmtTime(simSec: number) {
  const total = Math.floor(simSec) % 86400;
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}`;
}
