'use client';

import React from 'react';
import { CapacityOutput } from '../lib/types';
import { calculateAcres } from '../lib/footprint';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import { Zap, AlertTriangle, Check, X, Sliders, Info } from 'lucide-react';

interface SiteControlsProps {
  capacity: CapacityOutput;
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

  return (
    <Card className="border-border bg-card shadow-sm">
      <CardHeader className="pb-4 border-b border-border/60">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="text-xs uppercase tracking-wider font-semibold text-emerald-600 dark:text-emerald-400">
              Grid Connection Review
            </div>
            <CardTitle className="text-lg font-bold flex items-center gap-2 mt-1">
              <span>{capacity.serving_substation || 'Primary Substation'}</span>
              {capacity.voltage_kv && (
                <Badge variant="secondary" className="font-mono text-xs">
                  {capacity.voltage_kv} kV
                </Badge>
              )}
            </CardTitle>
          </div>

          {/* Flexible Toggle with shadcn Switch */}
          <div className="flex items-center gap-2.5 bg-muted/50 px-3 py-1.5 rounded-lg border border-border">
            <label
              htmlFor="flexible-toggle"
              className="text-xs font-medium text-foreground cursor-pointer select-none"
            >
              Flexible Connection
            </label>
            <Switch
              id="flexible-toggle"
              checked={flexibleConnection}
              onCheckedChange={onFlexibleToggle}
            />
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-5 pt-5">
        {/* Prompts for below-floor or non-viable */}
        {isBelowFloorFirm && !flexibleConnection && (
          <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div className="text-xs text-amber-900 dark:text-amber-200 space-y-1">
              <p className="font-semibold">Firm headroom below 5 MW floor ({firmMw} MW firm)</p>
              <p>
                This site has {ceilingMw} MW ceiling capacity. Enable{' '}
                <button
                  type="button"
                  onClick={() => onFlexibleToggle(true)}
                  className="underline font-bold hover:opacity-80"
                >
                  flexible connection
                </button>{' '}
                to unlock capacity above 5 MW.
              </p>
            </div>
          </div>
        )}

        {/* Capacity Slider & Acreage Metrics */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm font-semibold">
              <Sliders className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <span>Target Capacity:</span>
              <span className="text-lg font-bold text-emerald-600 dark:text-emerald-400">
                {selectedCapacityMw} MW
              </span>
            </div>

            <Badge variant="outline" className="text-xs text-muted-foreground">
              Allowed: {minFloorMw} MW – {maxAllowedMw} MW
            </Badge>
          </div>

          {/* shadcn Slider Component */}
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

          {/* Headroom Marks */}
          <div className="flex justify-between text-[11px] text-muted-foreground font-mono">
            <span>{minFloorMw} MW (Min Floor)</span>
            <span>Firm: {firmMw} MW</span>
            <span>Ceiling: {ceilingMw} MW</span>
          </div>

          {/* Curtailment Alert if applicable */}
          {isCurtailed && (
            <div className="p-2.5 bg-blue-500/10 border border-blue-500/30 rounded-lg flex items-center gap-2 text-xs text-blue-900 dark:text-blue-200">
              <Info className="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0" />
              <span>
                Operating above {firmMw} MW firm capacity under flexible agreement. Curtailment risk applies.
              </span>
            </div>
          )}

          {/* Calculated Footprint Box */}
          <div className="grid grid-cols-3 gap-3 p-3 bg-muted/40 rounded-lg border border-border">
            <div>
              <div className="text-[11px] text-muted-foreground font-medium">Energy Storage</div>
              <div className="text-sm font-semibold text-foreground">
                {acreage.energyMWh} MWh
              </div>
              <div className="text-[10px] text-muted-foreground">4-hour duration</div>
            </div>
            <div>
              <div className="text-[11px] text-muted-foreground font-medium">Reserved Area</div>
              <div className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                {acreage.midAcres} acres
              </div>
              <div className="text-[10px] text-muted-foreground">
                ({acreage.minAcres} – {acreage.maxAcres} range)
              </div>
            </div>
            <div>
              <div className="text-[11px] text-muted-foreground font-medium">Binding Direction</div>
              <div className="text-sm font-semibold capitalize text-foreground">
                {capacity.binding_direction || 'Import'}
              </div>
              <div className="text-[10px] text-muted-foreground">
                Season: {capacity.binding_season || 'Summer'}
              </div>
            </div>
          </div>
        </div>
      </CardContent>

      <CardFooter className="pt-2 flex items-center gap-3">
        <Button
          type="button"
          onClick={onConfirm}
          disabled={submitting || selectedCapacityMw < minFloorMw || selectedCapacityMw > maxAllowedMw}
          className="flex-1 bg-emerald-600 hover:bg-emerald-500 text-white font-medium gap-2 text-sm shadow-sm"
        >
          <Check className="w-4 h-4" />
          <span>Confirm Site & Sizing</span>
        </Button>

        <Button
          type="button"
          variant="outline"
          onClick={onReject}
          disabled={submitting}
          className="gap-2 text-sm"
        >
          <X className="w-4 h-4" />
          <span>Reject</span>
        </Button>
      </CardFooter>
    </Card>
  );
}
