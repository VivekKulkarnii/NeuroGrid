import { useState, useEffect, useRef, useCallback } from "react";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000/ws/grid";
const RECONNECT_DELAY = 3000;
const MAX_HISTORY = 300;

export type Scenario = "baseline" | "ai" | "stress";

// Shape of a single grid state from the backend
export interface GridState {
  hour_of_day: number;
  scenario: string;
  timestamp?: string | number;
  solar: {
    total_kw: number;
    panels: Array<{ output_kw: number; cloud_cover?: number }>;
  };
  houses: {
    total_kw: number;
    units: Array<{ id: string; name: string; load_kw: number }>;
  };
  ev_chargers: {
    total_kw: number;
    units: Array<{ id: string; connected: boolean; load_kw: number; battery_soc?: number }>;
  };
  battery: {
    soc: number;
    energy_kwh: number;
    capacity_kwh: number;
    available_charge_kw: number;
    available_discharge_kw: number;
  };
  grid: {
    total_demand_kw: number;
    net_import_kw: number;
    battery_power_kw: number;
    blackout: boolean;
  };
  price: {
    import_rate: number;
    export_rate?: number;
    tier: "peak" | "shoulder" | "off_peak";
  };
  metrics: {
    total_cost: number;
    blackout_count: number;
    step_count?: number;
  };
  battery_action?: number;
  ai_action?: {
    reason: string;
    controller: string;
    battery_action: number;
    ev_throttle: number;
    tone?: "info" | "good" | "warn" | "bad";
  };
}

export interface ActionEntry {
  id: number;
  t: number; // hour_of_day
  step: number | string;
  agent: string;
  text: string;
  controller: string;
  tone: "info" | "good" | "warn" | "bad";
}

export function useGridWebSocket() {
  const [connected, setConnected] = useState(false);
  const [paused, setPaused] = useState(false);
  const [currentState, setCurrentState] = useState<GridState | null>(null);
  const [history, setHistory] = useState<GridState[]>([]);
  const [actionLog, setActionLog] = useState<ActionEntry[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const actionIdRef = useRef(1);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      console.log("[WS] Connected to backend");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        // Batch history sent on connect
        if (data.type === "history") {
          setHistory(data.data || []);
          return;
        }

        // Scenario change acknowledgement
        if (data.type === "scenario_change") return;

        // Pause state update
        if (data.type === "pause_state") {
          setPaused(data.paused);
          return;
        }

        // Regular state tick
        const state = data as GridState;
        setCurrentState(state);

        setHistory((prev) => {
          const next = [...prev, state];
          return next.length > MAX_HISTORY ? next.slice(-MAX_HISTORY) : next;
        });

        // Collect AI action entries
        if (state.ai_action) {
          const entry: ActionEntry = {
            id: actionIdRef.current++,
            t: state.hour_of_day,
            step: state.timestamp ?? 0,
            agent: state.ai_action.controller ?? "AGENT",
            controller: state.ai_action.controller ?? "unknown",
            text: state.ai_action.reason ?? "—",
            tone: state.ai_action.tone ?? "info",
          };
          setActionLog((prev) => {
            const next = [entry, ...prev];
            return next.length > 100 ? next.slice(0, 100) : next;
          });
        }
      } catch (e) {
        console.error("[WS] Failed to parse message:", e);
      }
    };

    ws.onclose = () => {
      setConnected(false);
      console.log("[WS] Disconnected. Reconnecting in 3 s…");
      reconnectTimer.current = setTimeout(connect, RECONNECT_DELAY);
    };

    ws.onerror = () => {
      console.error("[WS] Error — closing socket");
      ws.close();
    };
  }, []);

  useEffect(() => {
    connect();
    return () => {
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const sendCommand = useCallback((command: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(command));
    }
  }, []);

  const setScenario = useCallback(
    (scenario: Scenario) => sendCommand({ action: "set_scenario", scenario }),
    [sendCommand],
  );

  const injectEvent = useCallback(
    (eventType: string, intensity = 1.0) =>
      sendCommand({ action: "inject_event", event_type: eventType, intensity }),
    [sendCommand],
  );

  const pauseSimulation = useCallback(() => {
    sendCommand({ action: "pause" });
    setPaused(true);
  }, [sendCommand]);

  const resumeSimulation = useCallback(() => {
    sendCommand({ action: "resume" });
    setPaused(false);
  }, [sendCommand]);

  const resetSimulation = useCallback(() => {
    sendCommand({ action: "reset" });
    setPaused(false);
    setHistory([]);
    setActionLog([]);
  }, [sendCommand]);

  return {
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
  };
}

/** Format a float hour-of-day (e.g. 14.5) → "02:30 PM" */
export function fmtHour(hour: number): string {
  const h = Math.floor(hour);
  const m = Math.round((hour - h) * 60);
  const period = h >= 12 ? "PM" : "AM";
  const displayH = h % 12 || 12;
  return `${displayH}:${String(m).padStart(2, "0")} ${period}`;
}
