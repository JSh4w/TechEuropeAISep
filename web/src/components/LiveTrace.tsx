'use client';

import React, { useEffect, useRef } from 'react';
import { TraceEvent } from '../lib/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Activity, Clock } from 'lucide-react';

interface LiveTraceProps {
  events: TraceEvent[];
  isConnected?: boolean;
  status?: string;
}

const STAGE_VARIANTS: Record<string, string> = {
  location: 'bg-indigo-500/15 text-indigo-700 dark:text-indigo-300 border-indigo-500/30',
  capacity: 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30',
  title: 'bg-sky-500/15 text-sky-700 dark:text-sky-300 border-sky-500/30',
  grid: 'bg-blue-500/15 text-blue-700 dark:text-blue-300 border-blue-500/30',
  planning: 'bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30',
  financial: 'bg-purple-500/15 text-purple-700 dark:text-purple-300 border-purple-500/30',
  synthesis: 'bg-teal-500/15 text-teal-700 dark:text-teal-300 border-teal-500/30',
};

export default function LiveTrace({
  events,
  isConnected = false,
  status = 'running',
}: LiveTraceProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events]);

  return (
    <Card className="flex flex-col h-full shadow-sm overflow-hidden border-border bg-card">
      <CardHeader className="p-4 border-b border-border/60 bg-muted/30">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-semibold flex items-center gap-2">
            <Activity className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>Agent Live Trace</span>
          </CardTitle>

          <div>
            {isConnected ? (
              <Badge variant="outline" className="flex items-center gap-1.5 text-xs text-emerald-600 dark:text-emerald-400 font-medium border-emerald-500/30 bg-emerald-500/10">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                Streaming
              </Badge>
            ) : (
              <Badge variant="outline" className="text-xs text-muted-foreground flex items-center gap-1">
                <Clock className="w-3 h-3" />
                <span className="capitalize">{status}</span>
              </Badge>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-0 flex-1">
        <div
          ref={scrollRef}
          className="p-4 overflow-y-auto space-y-3 font-mono text-xs max-h-[460px] min-h-[220px]"
        >
          {events.length === 0 ? (
            <div className="text-muted-foreground text-center py-10 font-sans text-sm">
              Waiting for pipeline events...
            </div>
          ) : (
            events.map((ev) => {
              const badgeStyle =
                STAGE_VARIANTS[ev.stage.toLowerCase()] ||
                'bg-muted text-muted-foreground border-border';

              return (
                <div
                  key={ev.id}
                  className="flex items-start gap-2.5 pb-2 border-b border-border/40 last:border-0"
                >
                  <span className="text-muted-foreground/60 text-[10px] w-6 shrink-0 text-right pt-0.5">
                    #{ev.id}
                  </span>

                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] uppercase font-semibold shrink-0 border ${badgeStyle}`}
                  >
                    {ev.stage}
                  </span>

                  <div className="flex-1 text-foreground break-words leading-relaxed font-sans">
                    {ev.msg}
                  </div>

                  <span className="text-muted-foreground text-[10px] shrink-0 pt-0.5">
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
        </div>
      </CardContent>
    </Card>
  );
}
