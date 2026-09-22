'use client';

import React from 'react';
import { CapacityOutput } from '../lib/types';
import { calculateAcres } from '../lib/footprint';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Zap, AlertTriangle, Check, X, Sliders, Info, Box, Layers, Loader2 } from 'lucide-react';

interface SiteControlsProps {
  capacity: CapacityOutput;
  loading?: boolean;
  selectedCapacityMw: number;
  onCapacityChange: (mw: number) => void;
  flexibleConnection: boolean;
  onFlexibleToggle: (enabled: boolean) => void;
  onConfirm: () => void;
  onReject: () => void;
  submitting?: boolean;
}

export default function SiteControls({
  capacity,
  loading = false,
  selectedCapacityMw,
  onCapacityChange,
  flexibleConnection,
  onFlexibleToggle,
  onConfirm,
  onReject,
  submitting = false,
}: SiteControlsProps) {
  const firmMw = capacity.firm_mw ?? 0;
  const ceilingMw = capacity.ceiling_mw ?? 0;
  const minFloorMw = 5;

  // Max selectable capacity: firm if flexible is off, ceiling if flexible is on
  const maxAllowedMw = flexibleConnection ? ceilingMw : firmMw;
  const isBelowFloorFirm = firmMw < minFloorMw && ceilingMw >= minFloorMw;
  const isCurtailed = flexibleConnection && selectedCapacityMw > firmMw;

  // Reserved acreage calculation
  const acreage = calculateAcres(selectedCapacityMw, 4);
  const estContainers = Math.ceil(acreage.energyMWh / 2.8); // ~2.8 MWh per standardized battery enclosure

  return (
    <Card className="relative border-border bg-card shadow-md rounded-2xl overflow-hidden">
      {loading && (
        <div className="absolute inset-0 z-10 bg-background/90 backdrop-blur-sm flex flex-col items-center justify-center gap-2">
          <Loader2 className="w-6 h-6 text-emerald-600 animate-spin" />
          <span className="text-xs font-semibold text-muted-foreground">Screening new location...</span>
        </div>
      )}
      <CardHeader className="p-5 border-b border-border/80 bg-muted/20">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="text-[11px] uppercase tracking-wider font-bold text-emerald-600 dark:text-emerald-400 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              Human-in-the-Loop Confirmation
            </div>
            <CardTitle className="text-xl font-bold flex items-center gap-2.5 mt-1 tracking-tight">
              <span>{loading ? '—' : capacity.serving_substation || 'Primary Substation'}</span>
              {!loading && capacity.voltage_kv && (
                <Badge variant="outline" className="font-mono text-xs font-semibold bg-blue-500/10 text-blue-600 border-blue-500/30">
                  {capacity.voltage_kv} kV Busbar
                </Badge>
              )}
            </CardTitle>
          </div>

          {/* Flexible Toggle with shadcn Switch */}
          <div className="flex items-center gap-3 bg-card px-3.5 py-2 rounded-xl border border-border shadow-xs">
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
            />
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-5 p-5">
        {/* Prompts for below-floor or non-viable */}
        {isBelowFloorFirm && !flexibleConnection && (
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
                {selectedCapacityMw} MW
              </span>
            </div>

            <div className="flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={() => onCapacityChange(Math.min(firmMw, maxAllowedMw))}
                disabled={firmMw < minFloorMw}
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
              max={Math.max(maxAllowedMw, minFloorMw)}
              step={0.5}
              value={[
                Math.min(
                  Math.max(selectedCapacityMw, minFloorMw),
                  Math.max(maxAllowedMw, minFloorMw)
                ),
              ]}
              disabled={maxAllowedMw < minFloorMw}
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
                {acreage.energyMWh} MWh
              </div>
              <div className="text-[10px] text-muted-foreground">4-Hour System Duration</div>
            </div>

            <div className="p-3 bg-muted/30 rounded-xl border border-border">
              <div className="text-[11px] text-muted-foreground font-medium flex items-center gap-1">
                <Box className="w-3.5 h-3.5 text-blue-600" />
                <span>BESS Enclosures</span>
              </div>
              <div className="text-base font-bold font-mono text-foreground mt-1">
                ~{estContainers} Units
              </div>
              <div className="text-[10px] text-muted-foreground">Modular BESS Enclosures</div>
            </div>

            <div className="p-3 bg-muted/30 rounded-xl border border-border">
              <div className="text-[11px] text-muted-foreground font-medium flex items-center gap-1">
                <Layers className="w-3.5 h-3.5 text-amber-600" />
                <span>Reserved Compound</span>
              </div>
              <div className="text-base font-bold font-mono text-emerald-600 dark:text-emerald-400 mt-1">
                {acreage.midAcres} Acres
              </div>
              <div className="text-[10px] text-muted-foreground">
                {(acreage.midAcres * 0.404686).toFixed(2)} Hectares footprint
              </div>
            </div>

            <div className="p-3 bg-muted/30 rounded-xl border border-border">
              <div className="text-[11px] text-muted-foreground font-medium">Consenting Route</div>
              <div className="text-base font-bold text-foreground mt-1 truncate">
                {selectedCapacityMw >= 50 ? 'NSIP (DCO)' : 'TCPA (Local)'}
              </div>
              <div className="text-[10px] text-muted-foreground">
                {selectedCapacityMw >= 50 ? 'Nationally Significant' : 'Town & Country Planning'}
              </div>
            </div>
          </div>
        </div>
      </CardContent>

      <CardFooter className="p-5 pt-0 flex items-center gap-3">
        <Button
          type="button"
          onClick={onConfirm}
          disabled={submitting || selectedCapacityMw < minFloorMw || selectedCapacityMw > maxAllowedMw}
          className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-semibold gap-2 text-sm h-11 rounded-xl shadow-md cursor-pointer transition active:scale-[0.99]"
        >
          <Check className="w-4 h-4 stroke-[3]" />
          <span>{submitting ? 'Running Feasibility & Valuation...' : 'Confirm Site & Run Feasibility'}</span>
        </Button>

        <Button
          type="button"
          variant="outline"
          onClick={onReject}
          disabled={submitting}
          className="gap-2 text-sm h-11 px-4 rounded-xl border-border hover:bg-destructive/10 hover:text-destructive hover:border-destructive/30 cursor-pointer"
        >
          <X className="w-4 h-4" />
          <span>Reject</span>
        </Button>
      </CardFooter>
    </Card>
  );
}
