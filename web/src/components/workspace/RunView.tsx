'use client';

import React from 'react';
import SiteMap from '../SiteMap';
import SiteControls from '../SiteControls';
import LiveTrace from '../LiveTrace';
import ReportView from '../ReportView';
import { Button } from '@/components/ui/button';
import { AlertCircle, Compass, Sparkles } from 'lucide-react';
import type { SiteRun } from '../../lib/useSiteRun';
import type { SiteData, SubstationOption } from '../../lib/types';

interface RunViewProps {
  run: SiteRun;
  onConfirm: () => void;
  onReset: () => void;
  /** Restarts the run with a flexible connection; offered when the not-viable message mentions it. */
  onRetryFlexible?: () => void;
  /** Shown next to the error message (e.g. a sign-in button). */
  errorAction?: React.ReactNode;
  /** Location input (and anything with it); sits above the map so the trace column starts at the top. */
  locationBar?: React.ReactNode;
  siteData?: SiteData | null;
  siteDataLoading?: boolean;
}

/** Location bar and status notices, then the report (when finished) or the map, capacity controls and live trace. */
export default function RunView({
  run,
  onConfirm,
  onReset,
  onRetryFlexible,
  errorAction,
  locationBar,
  siteData,
  siteDataLoading,
}: RunViewProps) {
  const { runStatus, capacityProposal, capacityLoading } = run;
  // The map's substation list is the alternates; the serving substation comes separately
  const serving: SubstationOption | null = capacityProposal?.serving_substation
    ? {
        name: capacityProposal.serving_substation,
        distance_km: capacityProposal.distance_km ?? 0,
        import_headroom_mw: capacityProposal.firm_mw ?? 0,
        export_headroom_mw: capacityProposal.firm_mw ?? 0,
        effective_headroom_mw: capacityProposal.firm_mw ?? 0,
        voltage_kv: capacityProposal.voltage_kv ?? 0,
        is_marginal: (capacityProposal.distance_km ?? 0) > 1,
      }
    : null;
  const notViableMessage =
    runStatus?.message || runStatus?.capacity?.message || 'Capacity is below the minimum viable connection threshold.';

  const notices = (
    <>
      {runStatus?.status === 'not_viable' && (
        <div className="p-4 bg-destructive/10 border border-destructive/30 rounded-xl flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-destructive shrink-0 mt-0.5" />
          <div className="text-xs text-foreground space-y-1">
            <p className="font-bold text-sm text-destructive">Site Not Viable for BESS Connection</p>
            <p>{notViableMessage}</p>
            {onRetryFlexible && !run.flexibleConnection && /flexible/i.test(notViableMessage) && (
              <div className="pt-2">
                <Button
                  type="button"
                  variant="destructive"
                  size="sm"
                  onClick={() => {
                    run.setFlexibleConnection(true);
                    onRetryFlexible();
                  }}
                  className="text-xs font-medium"
                >
                  Retry with Flexible Connection
                </Button>
              </div>
            )}
          </div>
        </div>
      )}

      {runStatus?.status === 'rejected' && (
        <div className="p-3 bg-muted/60 border border-border rounded-lg text-xs text-foreground flex items-center gap-2">
          <Compass className="w-4 h-4 text-muted-foreground shrink-0" />
          <span>Site declined. Enter a new location or drag the pin, then screen it again.</span>
        </div>
      )}

      {run.errorMsg && (
        <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-xs text-destructive flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{run.errorMsg}</span>
          </div>
          {errorAction}
        </div>
      )}
    </>
  );

  return run.result ? (
    <div className="space-y-6">
      {locationBar}
      {notices}
      <ReportView result={run.result} onReset={onReset} />
      <div className="max-w-3xl">
        <LiveTrace events={run.events} isConnected={false} status="completed" runId={run.runId} />
      </div>
    </div>
  ) : (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      {/* Left 3 cols: location bar, notices, interactive map & decision controls */}
      <div className="lg:col-span-3 space-y-4">
        {locationBar}
        {notices}

        {run.substationChangeNotice && (
          <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg text-xs text-blue-900 dark:text-blue-200 flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0" />
            <span>{run.substationChangeNotice}</span>
          </div>
        )}

        <SiteMap
          initialCenter={run.initialCenter}
          currentPosition={run.currentPosition}
          onPositionChange={(pos) => void run.moveTo(pos)}
          onPositionClamped={run.clampTo}
          capacityMw={run.selectedCapacityMw}
          substations={capacityLoading ? [] : capacityProposal?.alternates || []}
          servingSubstation={capacityLoading ? null : serving}
          servingPosition={capacityLoading ? null : capacityProposal?.substation_position}
          cableRoute={capacityLoading ? null : capacityProposal?.route}
          inspireGeoJson={run.inspireGeoJson}
          siteData={siteData}
          siteDataLoading={siteDataLoading}
        />

        {(capacityLoading || runStatus?.status === 'awaiting_confirmation') && capacityProposal && (
          <SiteControls
            capacity={capacityProposal}
            loading={capacityLoading}
            selectedCapacityMw={run.selectedCapacityMw}
            onCapacityChange={run.setSelectedCapacityMw}
            flexibleConnection={run.flexibleConnection}
            onFlexibleToggle={run.toggleFlexible}
            onConfirm={onConfirm}
            onExploreAnother={run.exploreAnother}
            submitting={run.submittingDecision}
          />
        )}
      </div>

      {/* Right col: live agent trace, level with the location bar */}
      <div className="lg:col-span-1 min-w-0">
        <LiveTrace events={run.events} isConnected={run.isStreaming} status={runStatus?.status || 'idle'} runId={run.runId} />
      </div>
    </div>
  );
}
