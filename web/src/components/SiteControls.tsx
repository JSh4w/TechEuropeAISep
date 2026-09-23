'use client';

import React, { useEffect, useRef, useState } from 'react';
import { CapacityOutput } from '../lib/types';
import { calculateAcres } from '../lib/footprint';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Zap, AlertTriangle, Play, Compass, Sliders, Info, Box, Layers, Loader2, ChevronDown } from 'lucide-react';

interface SiteControlsProps {
  /** Null until a screening returns capacity: the card then shows dashes under a blur. */
  capacity: CapacityOutput | null;
  /** Screening in flight: a spinner over the blur. */
  loading?: boolean;
  /** Shown over the blurred card when there is no capacity and nothing is loading. */
  placeholder?: string;
  selectedCapacityMw: number;
  onCapacityChange: (mw: number) => void;
  flexibleConnection: boolean;
  onFlexibleToggle: (enabled: boolean) => void;
  onConfirm: () => void;
  /** Declines this site so the user can pick another one. */
  onExploreAnother: () => void;
  submitting?: boolean;
  /** The site is confirmed and the engines are running: the card stays, its controls are locked. */
  running?: boolean;
}

export default function SiteControls({
  capacity,
  loading = false,
  placeholder = 'Screen a location to size the battery',
  selectedCapacityMw,
  onCapacityChange,
  flexibleConnection,
  onFlexibleToggle,
  onConfirm,
  onExploreAnother,
  submitting = false,
  running = false,
}: SiteControlsProps) {
  const empty = !capacity;
  const obscured = empty || loading;
  const ready = !obscured && !running;
  const busy = submitting || running;
  const firmMw = capacity?.firm_mw ?? 0;
  const ceilingMw = capacity?.ceiling_mw ?? 0;
  const minFloorMw = 5;

  // Max selectable capacity: firm if flexible is off, ceiling if flexible is on
  const maxAllowedMw = flexibleConnection ? ceilingMw : firmMw;
  const isBelowFloorFirm = firmMw < minFloorMw && ceilingMw >= minFloorMw;
  const isCurtailed = flexibleConnection && selectedCapacityMw > firmMw;
  // No flexible tier (e.g. live DNO data publishes firm only): the toggle would change nothing, so hide it.
  // Keep it in the blurred placeholder so the card layout does not jump.
  const hasFlexHeadroom = obscured || ceilingMw > firmMw;

  // Reserved acreage calculation
  const acreage = calculateAcres(selectedCapacityMw, 4);
  const estContainers = Math.ceil(acreage.energyMWh / 2.8); // ~2.8 MWh per standardized battery enclosure
  /** Dashes instead of numbers while there is no capacity to show. */
  const show = (value: string | number) => (empty ? '—' : value);

  // Once the capacity is in, a bouncing chevron points down to the card until its buttons have been on screen.
  const footerRef = useRef<HTMLDivElement>(null);
  const [footerVisible, setFooterVisible] = useState(true);
  const [seenFor, setSeenFor] = useState<CapacityOutput | null>(null);
  useEffect(() => {
    const el = footerRef.current;
    if (!ready || !el) return;
    const observer = new IntersectionObserver(([entry]) => {
      setFooterVisible(entry.isIntersecting);
      if (entry.isIntersecting) setSeenFor(capacity);
    }, { threshold: 0.5 });
    observer.observe(el);
    return () => observer.disconnect();
  }, [ready, capacity]);
  const showChevron = ready && !footerVisible && seenFor !== capacity;
  const blurred = obscured ? 'blur-[3px] select-none' : '';

  return (
    <Card className="relative border-border bg-card shadow-md rounded-2xl overflow-hidden">
      {obscured && (
        <div className="absolute inset-0 z-10 flex flex-col items-center justify-center gap-2" role="status">
          {loading ? (
            <>
              <Loader2 className="w-7 h-7 text-emerald-600 animate-spin" />
              <span className="text-xs font-semibold text-foreground">Screening location...</span>
            </>
          ) : (
            <span className="text-xs font-semibold text-muted-foreground bg-card/80 px-3 py-1.5 rounded-lg border border-border shadow-xs">
              {placeholder}
            </span>
          )}
        </div>
      )}
      {showChevron && (
        <button
          type="button"
          onClick={() => footerRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })}
          className="fixed bottom-4 left-1/2 -translate-x-1/2 z-40 text-emerald-700 hover:text-emerald-600 drop-shadow-[0_2px_4px_rgba(0,0,0,0.23)] cursor-pointer transition-colors"
          aria-label="Scroll down to confirm the site"
          title="Scroll down to confirm the site"
        >
          <ChevronDown className="w-16 h-16 animate-bounce" strokeWidth={2.5} />
        </button>
      )}
      <div
        inert={obscured}
        className="flex flex-col gap-(--card-spacing)"
      >
      <CardHeader className="p-5 border-b border-border/80 bg-muted/20">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="text-[11px] uppercase tracking-wider font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
              <span className={`w-1.5 h-1.5 rounded-full bg-emerald-500 ${ready ? 'animate-pulse' : ''}`}></span>
              Human-in-the-Loop Confirmation
            </div>
            <CardTitle className={`text-xl font-bold flex items-center gap-2.5 mt-1 tracking-tight ${blurred}`}>
              <span>{obscured ? '—' : capacity?.serving_substation || 'Primary Substation'}</span>
              {!obscured && capacity?.voltage_kv && (
                <Badge variant="outline" className="font-mono text-xs font-semibold bg-blue-500/10 text-blue-600 border-blue-500/30">
                  {capacity.voltage_kv} kV Busbar
                </Badge>
              )}
            </CardTitle>
          </div>

          {/* Flexible Toggle with shadcn Switch */}
          {hasFlexHeadroom && (
            <div className={`flex items-center gap-3 bg-card px-3.5 py-2 rounded-xl border border-border shadow-xs ${blurred}`}>
              <div className="text-right">
                <label
                  htmlFor="flexible-toggle"
                  className="text-xs font-semibold text-foreground block cursor-pointer select-none"
                >
                  Flexible Connection
                </label>
                <span className="text-[10px] text-muted-foreground">Unlocks ceiling capacity</span>
              </div>
              <Switch
                id="flexible-toggle"
                checked={flexibleConnection}
                onCheckedChange={onFlexibleToggle}
                disabled={busy}
              />
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent className={`space-y-5 p-5 ${blurred}`}>
        {/* Prompts for below-floor or non-viable */}
        {!empty && isBelowFloorFirm && !flexibleConnection && (
          <div className="p-3.5 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div className="text-xs text-amber-950 dark:text-amber-200 space-y-1">
              <p className="font-bold">Firm Headroom Below 5 MW Floor ({firmMw} MW firm)</p>
              <p>
                This substation provides {ceilingMw} MW flexible ceiling. Enable{' '}
                <button
                  type="button"
                  onClick={() => onFlexibleToggle(true)}
                  className="underline font-bold hover:opacity-80 cursor-pointer"
                >
                  flexible connection mode
                </button>{' '}
                to unlock capacity above 5 MW.
              </p>
            </div>
          </div>
        )}

        {/* Capacity Slider & Acreage Metrics */}
        <div className="space-y-3.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sliders className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <span className="text-sm font-semibold text-foreground">Target Export Capacity:</span>
              <span className="text-xl font-bold font-mono text-emerald-600 dark:text-emerald-400">
                {show(selectedCapacityMw)} MW
              </span>
            </div>

            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onCapacityChange(Math.min(firmMw, maxAllowedMw))}
                disabled={busy || firmMw < minFloorMw}
                className="text-[11px] h-6 px-2 font-mono"
              >
                Firm ({firmMw} MW)
              </Button>
              {flexibleConnection && ceilingMw > firmMw && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={() => onCapacityChange(ceilingMw)}
                  disabled={busy}
                  className="text-[11px] h-6 px-2 font-mono text-amber-600 dark:text-amber-400 border-amber-500/30"
                >
                  Ceiling ({ceilingMw} MW)
                </Button>
              )}
            </div>
          </div>

          {/* Slider Component */}
          <div className="pt-2 pb-1">
            <Slider
              min={minFloorMw}
              max={Math.max(maxAllowedMw, minFloorMw + 1)}
              step={0.5}
              value={[
                Math.min(
                  Math.max(selectedCapacityMw, minFloorMw),
                  Math.max(maxAllowedMw, minFloorMw + 1)
                ),
              ]}
              disabled={busy || maxAllowedMw < minFloorMw}
              onValueChange={(val) => {
                const nextVal = Array.isArray(val) ? val[0] : typeof val === 'number' ? val : selectedCapacityMw;
                onCapacityChange(nextVal);
              }}
            />
          </div>

          {/* Headroom Zone Markers */}
          <div className="flex justify-between items-center text-[11px] text-muted-foreground font-mono">
            <span className="flex items-center gap-1">
              <span className="w-2 h-2 rounded-full bg-zinc-400"></span>
              Floor: {minFloorMw} MW
            </span>
            <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400 font-semibold">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              Firm: {firmMw} MW
            </span>
            <span className="flex items-center gap-1 text-amber-600 dark:text-amber-400 font-semibold">
              <span className="w-2 h-2 rounded-full bg-amber-500"></span>
              Ceiling: {ceilingMw} MW
            </span>
          </div>

          {/* Curtailment Alert if applicable */}
          {isCurtailed && (
            <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-xl flex items-center gap-2 text-xs text-amber-900 dark:text-amber-200">
              <Info className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
              <span>
                Operating in flexible tier above {firmMw} MW firm headroom. Up to ~4.5% estimated annual curtailment factored into DCF.
              </span>
            </div>
          )}

          {/* Calculated Footprint Stat Tiles */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
            <div className="p-3 bg-muted/30 rounded-xl border border-border">
              <div className="text-[11px] text-muted-foreground font-medium flex items-center gap-1">
                <Zap className="w-3.5 h-3.5 text-emerald-600" />
                <span>Energy Capacity</span>
              </div>
              <div className="text-base font-bold font-mono text-foreground mt-1">
                {show(acreage.energyMWh)} MWh
              </div>
              <div className="text-[10px] text-muted-foreground">4-Hour System Duration</div>
            </div>

            <div className="p-3 bg-muted/30 rounded-xl border border-border">
              <div className="text-[11px] text-muted-foreground font-medium flex items-center gap-1">
                <Box className="w-3.5 h-3.5 text-blue-600" />
                <span>BESS Enclosures</span>
              </div>
              <div className="text-base font-bold font-mono text-foreground mt-1">
                ~{show(estContainers)} Units
              </div>
              <div className="text-[10px] text-muted-foreground">Modular BESS Enclosures</div>
            </div>

            <div className="p-3 bg-muted/30 rounded-xl border border-border">
              <div className="text-[11px] text-muted-foreground font-medium flex items-center gap-1">
                <Layers className="w-3.5 h-3.5 text-amber-600" />
                <span>Reserved Compound</span>
              </div>
              <div className="text-base font-bold font-mono text-emerald-600 dark:text-emerald-400 mt-1">
                {show(acreage.midAcres)} Acres
              </div>
              <div className="text-[10px] text-muted-foreground">
                {show((acreage.midAcres * 0.404686).toFixed(2))} Hectares footprint
              </div>
            </div>

            <div className="p-3 bg-muted/30 rounded-xl border border-border">
              <div className="text-[11px] text-muted-foreground font-medium">Consenting Route</div>
              <div className="text-base font-bold text-foreground mt-1 truncate">
                {empty ? '—' : selectedCapacityMw >= 50 ? 'NSIP (DCO)' : 'TCPA (Local)'}
              </div>
              <div className="text-[10px] text-muted-foreground">
                {empty ? 'Planning regime' : selectedCapacityMw >= 50 ? 'Nationally Significant' : 'Town & Country Planning'}
              </div>
            </div>
          </div>
        </div>
      </CardContent>

      <CardFooter ref={footerRef} className={`p-5 grid grid-cols-2 items-stretch sm:flex sm:items-center gap-3 ${blurred}`}>
        <Button
          type="button"
          onClick={onConfirm}
          disabled={busy || selectedCapacityMw < minFloorMw || selectedCapacityMw > maxAllowedMw}
          className="flex-1 min-w-0 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold gap-2 text-sm h-auto min-h-11 py-2 whitespace-normal leading-tight rounded-xl shadow-md cursor-pointer transition active:scale-[0.99]"
        >
          {busy ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4 fill-current" />}
          <span>{busy ? 'Running Feasibility & Valuation...' : 'Run feasibility'}</span>
        </Button>

        <Button
          type="button"
          variant="outline"
          onClick={onExploreAnother}
          disabled={busy}
          className="min-w-0 sm:w-1/3 shrink-0 gap-1.5 sm:gap-2 text-sm h-auto min-h-11 py-2 px-2 sm:px-4 whitespace-normal text-center leading-tight rounded-xl border-border hover:bg-muted/80 cursor-pointer"
        >
          <Compass className="w-4 h-4 shrink-0" />
          <span>Explore another location</span>
        </Button>
      </CardFooter>
      </div>
    </Card>
  );
}
