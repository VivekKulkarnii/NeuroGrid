import type { ActionEntry } from "@/hooks/useGridWebSocket";
import { fmtHour } from "@/hooks/useGridWebSocket";
import { useEffect, useRef } from "react";

const toneColor = {
  info: "var(--muted-foreground)",
  good: "var(--battery)",
  warn: "var(--solar)",
  bad: "var(--danger)",
} as const;

interface Props {
  actions: ActionEntry[];
  scenario?: string;
}

export function ActionLog({ actions, scenario }: Props) {
  const logRef = useRef<HTMLDivElement>(null);

  const scrollToLatest = () => {
    if (logRef.current) {
      logRef.current.scrollTo({ top: 0, behavior: "smooth" });
    }
  };

  // Auto-scroll to top only if we're already near the top
  useEffect(() => {
    if (logRef.current && logRef.current.scrollTop < 100) {
      logRef.current.scrollTop = 0;
    }
  }, [actions]);

  return (
    <div className="panel p-4 h-full flex flex-col">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <div>
            <div className="hud-label">Decision stream</div>
            <h3 className="font-display text-lg">Agent Log</h3>
          </div>
          <button
            onClick={scrollToLatest}
            className="mt-1 h-6 px-2 text-[10px] font-mono tracking-tighter border border-border hover:bg-surface-2 transition-colors rounded uppercase text-muted-foreground hover:text-foreground"
          >
            Jump to Latest
          </button>
        </div>
        <div className="flex items-center gap-2">
          {scenario && (
            <span
              className="font-mono text-[10px] tracking-widest px-2 py-1"
              style={{
                background: "rgba(129,140,248,0.1)",
                color: "#818cf8",
                borderRadius: 6,
              }}
            >
              {scenario}
            </span>
          )}
          <span className="font-mono text-[10px] text-muted-foreground">
            {actions.length} events
          </span>
        </div>
      </div>
      <div
        ref={logRef}
        className="flex-1 overflow-y-auto pr-1 space-y-2 font-mono text-[12px]"
      >
        {actions.length === 0 && (
          <div className="text-muted-foreground">
            No AI actions yet. Switch to AI or Stress scenario…
          </div>
        )}
        {actions.map((a) => (
          <div
            key={a.id}
            className="flex gap-2 border-l-2 pl-2 py-0.5"
            style={{ borderColor: toneColor[a.tone] }}
          >
            <span className="text-muted-foreground shrink-0">
              {fmtHour(a.t)}
            </span>
            <span
              className="shrink-0 px-1.5 text-[10px] tracking-widest"
              style={{ color: toneColor[a.tone] }}
            >
              {a.agent}
            </span>
            <span className="text-foreground/90">{a.text}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
