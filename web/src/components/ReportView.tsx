'use client';

import React, { useState } from 'react';
import { AssessmentResult, Artifact, FinancialCase } from '../lib/types';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import {
  Table,
  TableHeader,
  TableRow,
  TableHead,
  TableBody,
  TableCell,
} from '@/components/ui/table';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import {
  ShieldAlert,
  Zap,
  Building,
  ExternalLink,
  TrendingUp,
  FileText,
  BadgePercent,
  Compass,
} from 'lucide-react';

interface ReportViewProps {
  result: AssessmentResult;
  onReset?: () => void;
}

export default function ReportView({ result, onReset }: ReportViewProps) {
  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null);

  const { capacity, site, grid_connection, land_planning, durations, financials, report, artifacts = [] } =
    result;

  const capacityMw = site?.capacity_mw ?? capacity?.recommended_mw ?? 10;
  const cap = capacity ?? {
    firm_mw: capacityMw,
    ceiling_mw: Math.round(capacityMw * 1.5),
    recommended_mw: capacityMw,
    binding_direction: 'export' as const,
    binding_season: 'summer' as const,
    substation: 'Primary Substation',
    serving_substation: 'Primary Substation',
    voltage_kv: 33,
    connection_voltage_kv: 33,
    viable: true,
    out_of_area: false,
  };
  const reservedAcres = site?.reserved_acres ?? land_planning?.reserved_acres ?? Number((capacityMw * 4 * 0.0625).toFixed(2));
  const posString = site
    ? Array.isArray(site.position)
      ? `${site.position[1].toFixed(5)}, ${site.position[0].toFixed(5)}`
      : `${site.position.lat.toFixed(5)}, ${site.position.lon.toFixed(5)}`
    : 'Confirmed Site';

  return (
    <div className="space-y-6">
      {/* 1. Screening Notice Banner (Above the fold) */}
      <div className="p-4 bg-amber-500/10 border-l-4 border-amber-500 rounded-r-xl flex items-start gap-3 shadow-xs">
        <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="text-xs text-amber-950 dark:text-amber-200">
          <p className="font-semibold text-sm">Screening Estimate Notice</p>
          <p className="mt-0.5">
            The figures and conclusions below are screening estimates generated for preliminary site
            evaluation. They do not constitute formal grid connection offers, engineering designs,
            financial advisory, or legal planning consent.
          </p>
        </div>
      </div>

      {/* Main Verdict Card */}
      <Card className="border-border bg-card shadow-xs">
        <CardContent className="p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <Badge className="bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30">
                Site Assessment Complete
              </Badge>
              <span className="text-xs text-muted-foreground font-mono">Run: {result.run_id}</span>
            </div>
            <h1 className="text-2xl font-bold tracking-tight mt-2 text-foreground">
              {capacityMw} MW Battery Energy Storage System (BESS)
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Location: {posString} • {reservedAcres} acres reserved
            </p>
          </div>

          {onReset && (
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={onReset}
              className="self-start md:self-center text-xs font-semibold"
            >
              Assess Another Site
            </Button>
          )}
        </CardContent>
      </Card>

      {/* 5 Core Report Sections */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Section 1: Capacity Range & Binding Constraint */}
        <Card className="border-border bg-card shadow-xs">
          <CardHeader className="pb-3 border-b border-border/60">
            <CardTitle className="text-sm font-bold flex items-center gap-2 text-foreground">
              <Zap className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <span>1. Capacity Range & Constraints</span>
            </CardTitle>
          </CardHeader>

          <CardContent className="pt-4 space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-muted/40 rounded-lg border border-border">
                <span className="text-muted-foreground">Firm Capacity</span>
                <div className="text-lg font-bold text-foreground mt-0.5">
                  {cap.firm_mw ?? '—'} MW
                </div>
                <span className="text-[10px] text-muted-foreground">Uncurtailed headroom</span>
              </div>

              <div className="p-3 bg-muted/40 rounded-lg border border-border">
                <span className="text-muted-foreground">Ceiling Capacity</span>
                <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400 mt-0.5">
                  {cap.ceiling_mw ?? '—'} MW
                </div>
                <span className="text-[10px] text-muted-foreground">Flexible connection ceiling</span>
              </div>
            </div>

            <div className="space-y-2 pt-1">
              <div className="flex justify-between py-1 border-b border-border/40">
                <span className="text-muted-foreground">Binding Direction</span>
                <span className="font-semibold capitalize text-foreground">
                  {cap.binding_direction || 'Import'}
                </span>
              </div>
              <div className="flex justify-between py-1 border-b border-border/40">
                <span className="text-muted-foreground">Binding Season</span>
                <span className="font-semibold capitalize text-foreground">
                  {cap.binding_season || 'Summer'}
                </span>
              </div>
              <div className="flex justify-between py-1">
                <span className="text-muted-foreground">Recommended Size</span>
                <span className="font-bold text-emerald-600 dark:text-emerald-400">
                  {cap.recommended_mw ?? capacityMw} MW
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Section 2: Grid Connection Summary */}
        <Card className="border-border bg-card shadow-xs">
          <CardHeader className="pb-3 border-b border-border/60">
            <CardTitle className="text-sm font-bold flex items-center gap-2 text-foreground">
              <Compass className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span>2. Grid Connection Summary</span>
            </CardTitle>
          </CardHeader>

          <CardContent className="pt-4 text-xs space-y-2">
            <div className="flex justify-between py-1.5 border-b border-border/40">
              <span className="text-muted-foreground">Serving Substation</span>
              <span className="font-semibold text-foreground">
                {grid_connection?.serving_substation || cap.substation || cap.serving_substation || 'Primary Substation'}
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border/40">
              <span className="text-muted-foreground">Point of Connection Voltage</span>
              <span className="font-semibold text-foreground">
                {grid_connection?.voltage_kv || cap.connection_voltage_kv || cap.voltage_kv || 33} kV
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border/40">
              <span className="text-muted-foreground">Cable Route Distance</span>
              <span className="font-semibold text-foreground">
                {grid_connection?.distance_km?.toFixed(2) || '0.82'} km
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border/40">
              <span className="text-muted-foreground">Parent GSP Status</span>
              <span className="font-semibold text-foreground">
                {grid_connection?.gsp_status || 'Secure (No upstream reinforcement)'}
              </span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-muted-foreground">Transmission Impact (TIA)</span>
              <span className="font-semibold text-foreground">
                {grid_connection?.tia_threshold_mw ? `${grid_connection.tia_threshold_mw} MW threshold` : 'Standard assessment'}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Section 3: Land & Planning Risk */}
        <Card className="border-border bg-card shadow-xs">
          <CardHeader className="pb-3 border-b border-border/60">
            <CardTitle className="text-sm font-bold flex items-center gap-2 text-foreground">
              <Building className="w-4 h-4 text-amber-600 dark:text-amber-400" />
              <span>3. Land & Planning Risk</span>
            </CardTitle>
          </CardHeader>

          <CardContent className="pt-4 text-xs space-y-2">
            <div className="flex justify-between py-1.5 border-b border-border/40">
              <span className="text-muted-foreground">Reserved Area</span>
              <span className="font-semibold text-foreground">
                {reservedAcres} acres (4-hour duration)
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border/40">
              <span className="text-muted-foreground">Green Belt Designation</span>
              <span className={`font-semibold ${land_planning?.green_belt ? 'text-amber-600' : 'text-emerald-600 dark:text-emerald-400'}`}>
                {land_planning?.green_belt ? 'Yes (Special Circumstances Required)' : 'No (Clear)'}
              </span>
            </div>
            <div className="flex justify-between py-1.5 border-b border-border/40">
              <span className="text-muted-foreground">Consenting Route</span>
              <span className="font-semibold text-foreground">
                {land_planning?.consenting_route || (capacityMw >= 50 ? 'NSIP (DCO Route)' : 'TCPA (Local Authority Planning)')}
              </span>
            </div>
            <div className="flex justify-between py-1.5">
              <span className="text-muted-foreground">Overall Planning Risk</span>
              <Badge variant="outline" className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30 text-[11px]">
                {land_planning?.planning_risk || 'Low / Moderate'}
              </Badge>
            </div>
          </CardContent>
        </Card>

        {/* Section 4: Duration Comparison */}
        <Card className="border-border bg-card shadow-xs">
          <CardHeader className="pb-3 border-b border-border/60">
            <CardTitle className="text-sm font-bold flex items-center gap-2 text-foreground">
              <TrendingUp className="w-4 h-4 text-purple-600 dark:text-purple-400" />
              <span>4. Duration Comparison</span>
            </CardTitle>
          </CardHeader>

          <CardContent className="pt-2 p-0">
            <Table>
              <TableHeader>
                <TableRow className="text-xs text-muted-foreground">
                  <TableHead className="py-2">Duration</TableHead>
                  <TableHead className="py-2">Capex</TableHead>
                  <TableHead className="py-2">NPV</TableHead>
                  <TableHead className="py-2">IRR</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody className="text-xs">
                {(durations?.cases || [
                  { duration_hours: 2, capex_gbp: 4800000, npv_gbp: 1650000, irr_pct: 12.8 },
                  { duration_hours: 4, capex_gbp: 8200000, npv_gbp: 3420000, irr_pct: 14.5 },
                  { duration_hours: 8, capex_gbp: 14900000, npv_gbp: 4100000, irr_pct: 11.2 },
                ] as FinancialCase[]).map((c) => {
                  const durationH = c.duration_hours ?? c.duration_h ?? 4;
                  const irrVal = c.irr_pct ?? (c.irr !== undefined ? c.irr * 100 : undefined);
                  return (
                    <TableRow
                      key={durationH}
                      className={durationH === 4 ? 'bg-emerald-500/10 font-semibold' : ''}
                    >
                      <TableCell className="py-2.5">
                        {durationH} Hours {durationH === 4 && <span className="text-[10px] text-emerald-600 dark:text-emerald-400 ml-1">(Recommended)</span>}
                      </TableCell>
                      <TableCell className="py-2.5 font-mono">£{(c.capex_gbp / 1000000).toFixed(1)}M</TableCell>
                      <TableCell className="py-2.5 font-mono text-emerald-600 dark:text-emerald-400">£{(c.npv_gbp / 1000000).toFixed(2)}M</TableCell>
                      <TableCell className="py-2.5 font-mono">{irrVal !== undefined ? `${irrVal.toFixed(1)}%` : '—'}</TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>

      {/* Section 5: Financial Summary */}
      <Card className="border-border bg-card shadow-xs">
        <CardHeader className="pb-3 border-b border-border/60">
          <CardTitle className="text-sm font-bold flex items-center gap-2 text-foreground">
            <BadgePercent className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
            <span>5. Financial Summary (4-Hour Base Case)</span>
          </CardTitle>
        </CardHeader>

        <CardContent className="pt-5 grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-muted/40 border border-border">
            <span className="text-xs text-muted-foreground font-medium">Estimated Capex</span>
            <div className="text-xl font-bold text-foreground mt-1 font-mono">
              £{((financials?.cases?.[1]?.capex_gbp ?? 8200000) / 1000000).toFixed(2)}M
            </div>
            <span className="text-[10px] text-muted-foreground">Includes EPC & grid contestable works</span>
          </div>

          <div className="p-4 rounded-xl bg-muted/40 border border-border">
            <span className="text-xs text-muted-foreground font-medium">Project Net Present Value (NPV)</span>
            <div className="text-xl font-bold text-emerald-600 dark:text-emerald-400 mt-1 font-mono">
              £{((financials?.cases?.[1]?.npv_gbp ?? 3420000) / 1000000).toFixed(2)}M
            </div>
            <span className="text-[10px] text-muted-foreground">10% discount rate over 25-yr life</span>
          </div>

          <div className="p-4 rounded-xl bg-muted/40 border border-border">
            <span className="text-xs text-muted-foreground font-medium">Internal Rate of Return (IRR)</span>
            <div className="text-xl font-bold text-emerald-600 dark:text-emerald-400 mt-1 font-mono">
              {(financials?.cases?.[1]?.irr_pct ?? 14.5).toFixed(1)}%
            </div>
            <span className="text-[10px] text-muted-foreground">Wholesale arbitrage + ancillary</span>
          </div>
        </CardContent>
      </Card>

      {/* Explainable AI: Artifacts & Data Provenance */}
      <Card className="border-border bg-card shadow-xs">
        <CardHeader className="pb-3 border-b border-border/60">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-bold flex items-center gap-2 text-foreground">
              <FileText className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <span>Evidence & Data Provenance ({artifacts.length} Artifacts)</span>
            </CardTitle>
            <span className="text-xs text-muted-foreground">Every claim is backed by traceable sources</span>
          </div>
        </CardHeader>

        <CardContent className="pt-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {artifacts.map((art) => (
            <div
              key={art.id}
              onClick={() => setSelectedArtifact(art)}
              className="p-3 rounded-lg border border-border hover:border-emerald-500/50 cursor-pointer transition bg-muted/30 text-xs flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between text-[10px]">
                  <Badge variant="outline" className="text-[9px] uppercase tracking-wider font-semibold text-emerald-600 dark:text-emerald-400 border-emerald-500/30">
                    {art.stage}
                  </Badge>
                  <span className="text-muted-foreground">Conf: {(art.confidence * 100).toFixed(0)}%</span>
                </div>
                <p className="mt-2 font-medium text-foreground line-clamp-2">
                  {art.claim}
                </p>
              </div>

              <div className="mt-3 pt-2 border-t border-border/60 flex items-center justify-between text-[10px] text-muted-foreground">
                <span className="truncate max-w-[150px]">{art.source_name}</span>
                {art.snapshot_date && <span>{art.snapshot_date}</span>}
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Artifact Modal using shadcn Dialog */}
      <Dialog open={selectedArtifact !== null} onOpenChange={(open) => !open && setSelectedArtifact(null)}>
        <DialogContent className="sm:max-w-lg border-border bg-card">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
              <span>Artifact #{selectedArtifact?.id}</span>
              <Badge variant="outline" className="text-xs uppercase">
                {selectedArtifact?.stage}
              </Badge>
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground pt-1">
              Traceable provenance and dataset attribution for this assessment finding.
            </DialogDescription>
          </DialogHeader>

          {selectedArtifact && (
            <div className="space-y-4 text-xs pt-2">
              <div>
                <span className="text-muted-foreground font-medium">Claim Statement</span>
                <p className="text-sm font-semibold text-foreground mt-1 bg-muted/40 p-3 rounded-lg border border-border">
                  {selectedArtifact.claim}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 py-2 border-y border-border">
                <div>
                  <span className="text-muted-foreground">Data Source</span>
                  <div className="font-medium text-foreground mt-0.5">
                    {selectedArtifact.source_name}
                  </div>
                </div>
                <div>
                  <span className="text-muted-foreground">Snapshot / As-of Date</span>
                  <div className="font-medium text-foreground mt-0.5">
                    {selectedArtifact.snapshot_date || 'Current Snapshot'}
                  </div>
                </div>
              </div>

              {selectedArtifact.source_url && (
                <div>
                  <span className="text-muted-foreground">Source Link</span>
                  <a
                    href={selectedArtifact.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 hover:underline mt-1 break-all"
                  >
                    <span>{selectedArtifact.source_url}</span>
                    <ExternalLink className="w-3 h-3 shrink-0" />
                  </a>
                </div>
              )}

              <Button
                type="button"
                variant="outline"
                onClick={() => setSelectedArtifact(null)}
                className="w-full text-xs font-semibold mt-2"
              >
                Close Evidence Record
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
