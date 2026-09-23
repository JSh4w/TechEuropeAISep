'use client';

import React, { useEffect, useRef, useState } from 'react';
import { TraceEvent } from '../lib/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Activity,
  Clock,
  Terminal,
  ArrowDown,
  MapPin,
  Zap,
  Building,
  Coins,
  Sparkles,
  FileCheck,
} from 'lucide-react';

interface LiveTraceProps {
  events: TraceEvent[];
  isConnected?: boolean;
  status?: string;
  /** Temporal workflow id of the run, shown under the title once a run exists. */
  runId?: string | null;
}

const STAGE_CONFIG: Record<
  string,
  { badge: string; icon: React.ReactNode }
> = {
  location: {
    badge: 'bg-indigo-500/10 text-indigo-700 dark:text-indigo-300 border-indigo-500/30',
    icon: <MapPin className="w-3 h-3 text-indigo-500" />,
  },
  capacity: {
    badge: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30',
    icon: <Zap className="w-3 h-3 text-emerald-500" />,
  },
  title: {
    badge: 'bg-sky-500/10 text-sky-700 dark:text-sky-300 border-sky-500/30',
    icon: <FileCheck className="w-3 h-3 text-sky-500" />,
  },
  grid: {
    badge: 'bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/30',
    icon: <Zap className="w-3 h-3 text-blue-500" />,
  },
  planning: {
    badge: 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30',
    icon: <Building className="w-3 h-3 text-amber-500" />,
  },
  financial: {
    badge: 'bg-purple-500/10 text-purple-700 dark:text-purple-300 border-purple-500/30',
    icon: <Coins className="w-3 h-3 text-purple-500" />,
  },
  synthesis: {
    badge: 'bg-teal-500/10 text-teal-700 dark:text-teal-300 border-teal-500/30',
    icon: <Sparkles className="w-3 h-3 text-teal-500" />,
  },
};

export default function LiveTrace({
  events,
  isConnected = false,
  status = 'running',
  runId = null,
}: LiveTraceProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [autoScroll, setAutoScroll] = useState(true);

  useEffect(() => {
    if (autoScroll && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events, autoScroll]);

  return (
    <Card className="flex flex-col h-full shadow-md rounded-2xl overflow-hidden border-border bg-card">
      <CardHeader className="p-4 border-b border-border/80 bg-muted/20">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            <div className="p-1 rounded-md bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
              <Terminal className="w-4 h-4" />
            </div>
            <div className="min-w-0">
              <CardTitle className="text-sm font-bold tracking-tight">Agent Telemetry</CardTitle>
              <div className="text-[10px] text-muted-foreground font-mono truncate" title={runId ?? undefined}>
                {runId ?? 'Temporal Workflow Stream'}
              </div>
            </div>
          </div>

          <div className="flex items-center gap-2 min-w-0 max-w-full">
            {isConnected ? (
              <Badge variant="outline" className="flex items-center gap-1.5 text-[11px] text-emerald-600 dark:text-emerald-400 font-semibold border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                SSE Active
              </Badge>
            ) : (
              <Badge variant="outline" className="text-[11px] text-muted-foreground font-mono flex items-center gap-1 px-2 py-0.5 max-w-full" title={status}>
                <Clock className="w-3 h-3 shrink-0" />
                <span className="capitalize truncate">{status.replace(/_/g, ' ')}</span>
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-0 flex-1 flex flex-col justify-between">
        <div
          ref={scrollRef}
          onScroll={(e) => {
            const el = e.currentTarget;
            const isNearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
            setAutoScroll(isNearBottom);
          }}
          className="p-4 overflow-y-auto space-y-2.5 font-mono text-xs max-h-[460px] min-h-[300px]"
        >
          {events.length === 0 ? (
            <div className="text-muted-foreground text-center py-16 font-sans text-xs flex flex-col items-center gap-2">
              <Activity className="w-6 h-6 text-muted-foreground/40 animate-pulse" />
              <span>Awaiting pipeline execution events...</span>
              <span className="text-[10px] text-muted-foreground/70">Enter a UK postcode or click a demo site above</span>
            </div>
          ) : (
            events.map((ev) => {
              const cfg = STAGE_CONFIG[ev.stage.toLowerCase()] || {
                badge: 'bg-muted text-muted-foreground border-border',
                icon: <Activity className="w-3 h-3 text-muted-foreground" />,
              };

              return (
                <div
                  key={ev.id}
                  className="flex items-start gap-2.5 p-2 rounded-xl bg-muted/20 border border-border/50 hover:bg-muted/40 transition"
                >
                  <span className="text-muted-foreground/60 text-[10px] w-5 shrink-0 text-right pt-0.5">
                    {ev.id}
                  </span>

                  <div className="shrink-0 flex items-center gap-1">
                    <span
                      className={`inline-flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] uppercase font-bold border ${cfg.badge}`}
                    >
                      {cfg.icon}
                      <span>{ev.stage}</span>
                    </span>
                  </div>

                  <div className="flex-1 min-w-0 text-foreground text-xs leading-relaxed font-sans pt-0.5 [overflow-wrap:anywhere]">
                    {ev.msg}
                  </div>

                  <span className="text-muted-foreground/70 text-[10px] shrink-0 font-mono pt-0.5">
                    {ev.t
                      ? new Date(ev.t).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                          second: '2-digit',
                        })
                      : ''}
                  </span>
                </div>
              );
            })
          )}

          {isConnected && events.length > 0 && (
            <div className="flex items-center gap-2 pt-1 text-[11px] text-emerald-600 dark:text-emerald-400 font-mono animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
              <span>Autonomous agent processing stage...</span>
            </div>
          )}
        </div>

        {/* Trace Footer Telemetry info */}
        <div className="p-3 border-t border-border/60 bg-muted/10 flex items-center justify-between text-[11px] text-muted-foreground font-mono">
          <span>{events.length} Events Logged</span>
          {!autoScroll && (
            <button
              type="button"
              onClick={() => {
                setAutoScroll(true);
                if (scrollRef.current) {
                  scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
                }
              }}
              className="text-emerald-600 dark:text-emerald-400 flex items-center gap-1 hover:underline cursor-pointer"
            >
              <span>Scroll to live</span>
              <ArrowDown className="w-3 h-3" />
            </button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
