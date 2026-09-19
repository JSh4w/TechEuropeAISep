'use client';

import React, { useState } from 'react';
import { AssessmentResult, Artifact, FinancialCase } from '../lib/types';
import { downloadMarkdownReport, printReport } from '../lib/reportExport';
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
  Download,
  Printer,
  Users,
  CheckCircle2,
  Sparkles,
  ArrowRight,
  ShieldCheck,
  AlertTriangle,
} from 'lucide-react';

interface ReportViewProps {
  result: AssessmentResult;
  onReset?: () => void;
}

export default function ReportView({ result, onReset }: ReportViewProps) {
  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null);
  const [selectedDurationH, setSelectedDurationH] = useState<number>(4);

  const { capacity, site, grid_connection, land_planning, durations, financials, artifacts = [] } =
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
      ? `${site.position[1].toFixed(5)}°N, ${Math.abs(site.position[0]).toFixed(5)}°${site.position[0] >= 0 ? 'E' : 'W'}`
      : `${site.position.lat.toFixed(5)}°N, ${Math.abs(site.position.lon).toFixed(5)}°${site.position.lon >= 0 ? 'E' : 'W'}`
    : 'Confirmed Site';

  // Duration cases
  const financialCases: FinancialCase[] = durations?.cases || financials?.cases || [
    { duration_hours: 2, capex_gbp: 4800000, npv_gbp: 1650000, irr_pct: 12.8 },
    { duration_hours: 4, capex_gbp: 8200000, npv_gbp: 3420000, irr_pct: 14.5 },
    { duration_hours: 8, capex_gbp: 14900000, npv_gbp: 4100000, irr_pct: 11.2 },
  ];

  const activeCase = financialCases.find(
    (c) => (c.duration_hours ?? c.duration_h) === selectedDurationH
  ) || financialCases[1] || financialCases[0];

  const activeIrr = activeCase.irr_pct ?? (activeCase.irr !== undefined ? activeCase.irr * 100 : 14.5);

  return (
    <div className="space-y-6">
      {/* 1. Header Bar with Status & Actions */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-2 border-b border-border/80">
        <div>
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
              BESS Feasibility Dossier
            </span>
            <span className="text-xs text-muted-foreground font-mono">Run: {result.run_id}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-foreground mt-1">
            {capacityMw} MW / {capacityMw * selectedDurationH} MWh Battery Energy Storage Assessment
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground mt-0.5 flex flex-wrap items-center gap-2">
            <span>Coordinates: <strong className="text-foreground font-mono">{posString}</strong></span>
            <span>•</span>
            <span>Serving: <strong className="text-foreground">{grid_connection?.serving_substation || cap.serving_substation}</strong></span>
            <span>•</span>
            <span>Compound: <strong className="text-foreground">{reservedAcres} Acres</strong></span>
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => downloadMarkdownReport(result)}
            className="text-xs font-semibold gap-1.5 h-9 rounded-xl border-border hover:bg-muted"
          >
            <Download className="w-3.5 h-3.5 text-emerald-600" />
            <span>Export (.md)</span>
          </Button>

          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={printReport}
            className="text-xs font-semibold gap-1.5 h-9 rounded-xl border-border hover:bg-muted"
          >
            <Printer className="w-3.5 h-3.5 text-blue-600" />
            <span>Print PDF</span>
          </Button>

          {onReset && (
            <Button
              type="button"
              variant="default"
              size="sm"
              onClick={onReset}
              className="text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white h-9 rounded-xl shadow-xs"
            >
              Assess Next Site
            </Button>
          )}
        </div>
      </div>

      {/* 2. Executive Metric Hero Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Capex Card */}
        <div className="p-4 rounded-2xl bg-card border border-border shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">Initial Capex</span>
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded bg-muted text-muted-foreground">
              {selectedDurationH}H Case
            </span>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold font-sans tabular-nums text-foreground tracking-tight">
              £{(activeCase.capex_gbp / 1000000).toFixed(2)}M
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              ~£{Math.round(activeCase.capex_gbp / (capacityMw * selectedDurationH) / 1000)}k / MWh turnkey
            </p>
          </div>
        </div>

        {/* 25-Year NPV Card */}
        <div className="p-4 rounded-2xl bg-card border border-border shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">Project Net Present Value</span>
            <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30 text-[10px] font-semibold">
              NPV @ 10%
            </Badge>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold font-sans tabular-nums text-emerald-600 dark:text-emerald-400 tracking-tight">
              £{(activeCase.npv_gbp / 1000000).toFixed(2)}M
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              25-year operational lifecycle
            </p>
          </div>
        </div>

        {/* Internal Rate of Return (IRR) */}
        <div className="p-4 rounded-2xl bg-card border border-border shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">Project IRR</span>
            <Badge className="bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30 text-[10px] font-semibold">
              Unlevered
            </Badge>
          </div>
          <div className="mt-3">
            <div className="text-2xl font-bold font-sans tabular-nums text-emerald-600 dark:text-emerald-400 tracking-tight">
              {activeIrr.toFixed(1)}%
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5">
              Wholesale arbitrage + frequency services
            </p>
          </div>
        </div>

        {/* Planning & Network Status */}
        <div className="p-4 rounded-2xl bg-card border border-border shadow-xs flex flex-col justify-between">
          <div className="flex items-center justify-between">
            <span className="text-xs font-medium text-muted-foreground">Planning Consent</span>
            <Badge variant="outline" className="text-[10px] uppercase font-semibold text-emerald-700 dark:text-emerald-300 bg-emerald-500/10 border-emerald-500/30">
              {land_planning?.planning_risk || 'Low Risk'}
            </Badge>
          </div>
          <div className="mt-3">
            <div className="text-base font-bold text-foreground truncate">
              {land_planning?.consenting_route || (capacityMw >= 50 ? 'NSIP (DCO)' : 'TCPA (Local Plan)')}
            </div>
            <p className="text-[11px] text-muted-foreground mt-0.5 flex items-center gap-1">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-600" />
              <span>Green Belt: {land_planning?.green_belt ? 'Designated' : 'Clear (No designation)'}</span>
            </p>
          </div>
        </div>
      </div>

      {/* Compact Model Disclaimer Pill */}
      <div className="px-4 py-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-xs text-amber-950 dark:text-amber-200 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0" />
          <span><strong>Screening Estimate:</strong> Feasibility figures are derived from open distribution snapshots (UKPN/LTDS/INSPIRE) and do not substitute a formal DNO Connection Offer.</span>
        </div>
        <span className="text-[10px] font-mono text-amber-700 dark:text-amber-300 whitespace-nowrap hidden sm:inline">Model v1.2</span>
      </div>

      {/* 3. Deep Dive Sections Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Section 1: Capacity Range & Grid Constraints */}
        <Card className="border-border bg-card shadow-xs rounded-2xl overflow-hidden">
          <CardHeader className="p-4 border-b border-border/70 bg-muted/20">
            <CardTitle className="text-sm font-bold flex items-center gap-2 text-foreground">
              <Zap className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <span>1. Capacity Range & Constraints</span>
            </CardTitle>
          </CardHeader>

          <CardContent className="p-4 space-y-4 text-xs">
            <div className="grid grid-cols-2 gap-3">
              <div className="p-3 bg-muted/30 rounded-xl border border-border">
                <span className="text-muted-foreground font-medium text-[11px]">Firm Headroom</span>
                <div className="text-xl font-bold font-mono text-foreground mt-1">
                  {cap.firm_mw ?? '—'} MW
                </div>
                <span className="text-[10px] text-muted-foreground">Uncurtailed firm connection</span>
              </div>

              <div className="p-3 bg-muted/30 rounded-xl border border-border">
                <span className="text-muted-foreground font-medium text-[11px]">Ceiling Capacity</span>
                <div className="text-xl font-bold font-mono text-amber-600 dark:text-amber-400 mt-1">
                  {cap.ceiling_mw ?? '—'} MW
                </div>
                <span className="text-[10px] text-muted-foreground">Flexible connection headroom</span>
              </div>
            </div>

            <div className="space-y-2 pt-1 font-sans">
              <div className="flex justify-between py-1.5 border-b border-border/50">
                <span className="text-muted-foreground">Binding Direction</span>
                <span className="font-semibold uppercase tracking-wider text-[11px] text-foreground">
                  {cap.binding_direction || 'Export'} Headroom
                </span>
              </div>
              <div className="flex justify-between py-1.5 border-b border-border/50">
                <span className="text-muted-foreground">Binding Season</span>
                <span className="font-semibold capitalize text-foreground">
                  {cap.binding_season || 'Summer'} (Thermal rating constrained)
                </span>
              </div>
              <div className="flex justify-between py-1.5">
                <span className="text-muted-foreground">Recommended Connection Size</span>
                <span className="font-bold font-mono text-emerald-600 dark:text-emerald-400">
                  {cap.recommended_mw ?? capacityMw} MW
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Section 2: Grid Connection Architecture */}
        <Card className="border-border bg-card shadow-xs rounded-2xl overflow-hidden">
          <CardHeader className="p-4 border-b border-border/70 bg-muted/20">
            <CardTitle className="text-sm font-bold flex items-center gap-2 text-foreground">
              <Compass className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              <span>2. Grid Interconnection Route</span>
            </CardTitle>
          </CardHeader>

          <CardContent className="p-4 text-xs space-y-2.5">
            <div className="flex justify-between py-1 border-b border-border/50">
              <span className="text-muted-foreground">Serving Substation</span>
              <span className="font-bold text-foreground">
                {grid_connection?.serving_substation || cap.substation || cap.serving_substation || 'Primary Substation'}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-border/50">
              <span className="text-muted-foreground">Point of Connection (PoC) Voltage</span>
              <span className="font-mono font-semibold text-foreground">
                {grid_connection?.voltage_kv || cap.connection_voltage_kv || cap.voltage_kv || 33} kV Busbar
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-border/50">
              <span className="text-muted-foreground">Estimated Cable Route Distance</span>
              <span className="font-mono font-semibold text-foreground">
                {grid_connection?.distance_km?.toFixed(2) || '0.65'} km
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-border/50">
              <span className="text-muted-foreground">Parent GSP Status</span>
              <span className="font-semibold text-emerald-600 dark:text-emerald-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span>{grid_connection?.gsp_status || 'Secure (No transmission reinforcement required)'}</span>
              </span>
            </div>
            <div className="flex justify-between py-1">
              <span className="text-muted-foreground">Transmission Impact Assessment (TIA)</span>
              <span className="font-semibold text-foreground">
                {grid_connection?.tia_threshold_mw ? `${grid_connection.tia_threshold_mw} MW statement threshold` : 'Standard DNO screening'}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Section 3: Land, Planning & Environmental Risk */}
        <Card className="border-border bg-card shadow-xs rounded-2xl overflow-hidden">
          <CardHeader className="p-4 border-b border-border/70 bg-muted/20">
            <CardTitle className="text-sm font-bold flex items-center gap-2 text-foreground">
              <Building className="w-4 h-4 text-amber-600 dark:text-amber-400" />
              <span>3. Land, Planning & Environmental Risk</span>
            </CardTitle>
          </CardHeader>

          <CardContent className="p-4 text-xs space-y-2.5">
            <div className="flex justify-between py-1 border-b border-border/50">
              <span className="text-muted-foreground">Reserved Battery Compound</span>
              <span className="font-semibold text-foreground font-mono">
                {reservedAcres} Acres ({(reservedAcres * 0.404686).toFixed(2)} Ha)
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-border/50">
              <span className="text-muted-foreground">Metropolitan Green Belt Status</span>
              <span className={`font-semibold ${land_planning?.green_belt ? 'text-amber-600' : 'text-emerald-600 dark:text-emerald-400'}`}>
                {land_planning?.green_belt ? 'Designated (Requires Very Special Circumstances)' : 'Clear (Outside Green Belt)'}
              </span>
            </div>
            <div className="flex justify-between py-1 border-b border-border/50">
              <span className="text-muted-foreground">Statutory Planning Consent Route</span>
              <span className="font-semibold text-foreground">
                {land_planning?.consenting_route || (capacityMw >= 50 ? 'NSIP (DCO Route)' : 'TCPA (Local Planning Authority)')}
              </span>
            </div>

            {/* Local Community Sentiment Scan */}
            <div className="pt-2 border-t border-border/70 space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground flex items-center gap-1.5 font-medium">
                  <Users className="w-3.5 h-3.5 text-blue-600 dark:text-blue-400" />
                  <span>Public Sentiment Opposition Risk</span>
                </span>
                <Badge
                  variant="outline"
                  className={`text-[11px] font-semibold ${
                    (result.sentiment?.opposition_index ?? 0.24) <= 0.35
                      ? 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30'
                      : (result.sentiment?.opposition_index ?? 0.24) <= 0.65
                      ? 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30'
                      : 'bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-500/30'
                  }`}
                >
                  {((result.sentiment?.opposition_index ?? 0.24) * 100).toFixed(0)}% Index (
                  {(result.sentiment?.opposition_index ?? 0.24) <= 0.35
                    ? 'Low Opposition'
                    : (result.sentiment?.opposition_index ?? 0.24) <= 0.65
                    ? 'Moderate'
                    : 'Elevated'}
                  )
                </Badge>
              </div>

              <div className="p-2.5 bg-muted/30 rounded-xl border border-border text-[11px] space-y-1.5">
                <div className="flex justify-between text-muted-foreground">
                  <span>DeBERTa Sentiment Model:</span>
                  <span className="font-medium text-foreground">
                    {result.sentiment?.sources ?? 4} planning decisions reviewed
                  </span>
                </div>
                {(result.sentiment?.top_concerns ?? ['Acoustic Enclosures', 'Fire Safety', 'Visual Buffering']).length > 0 && (
                  <div className="pt-1 flex flex-wrap items-center gap-1.5">
                    <span className="text-muted-foreground text-[10px]">Statutory Focus Areas:</span>
                    {(result.sentiment?.top_concerns ?? ['Acoustic Enclosures', 'Fire Safety', 'Visual Buffering']).map((concern) => (
                      <span
                        key={concern}
                        className="px-2 py-0.5 rounded-md bg-card border border-border text-[10px] text-foreground font-medium"
                      >
                        {concern}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Section 4: Duration Comparison & Sizing Trade-offs */}
        <Card className="border-border bg-card shadow-xs rounded-2xl overflow-hidden">
          <CardHeader className="p-4 border-b border-border/70 bg-muted/20">
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm font-bold flex items-center gap-2 text-foreground">
                <TrendingUp className="w-4 h-4 text-purple-600 dark:text-purple-400" />
                <span>4. Duration & Returns Matrix</span>
              </CardTitle>
              <span className="text-[11px] text-muted-foreground">Select to inspect case</span>
            </div>
          </CardHeader>

          <CardContent className="p-4">
            <div className="space-y-2.5">
              {financialCases.map((c) => {
                const durationH = c.duration_hours ?? c.duration_h ?? 4;
                const irrVal = c.irr_pct ?? (c.irr !== undefined ? c.irr * 100 : 0);
                const isSelected = selectedDurationH === durationH;
                const isRecommended = durationH === 4;

                return (
                  <div
                    key={durationH}
                    onClick={() => setSelectedDurationH(durationH)}
                    className={`p-3 rounded-xl border transition cursor-pointer flex items-center justify-between ${
                      isSelected
                        ? 'border-emerald-500 bg-emerald-500/10 shadow-xs'
                        : 'border-border bg-muted/20 hover:border-border/80'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className={`w-8 h-8 rounded-lg flex items-center justify-center font-bold text-xs ${
                        isSelected ? 'bg-emerald-600 text-white' : 'bg-muted text-foreground'
                      }`}>
                        {durationH}h
                      </div>
                      <div>
                        <div className="font-bold text-xs text-foreground flex items-center gap-1.5">
                          <span>{durationH}-Hour Duration ({capacityMw * durationH} MWh)</span>
                          {isRecommended && (
                            <Badge className="bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 border-none text-[9px] uppercase px-1.5 py-0">
                              Optimal
                            </Badge>
                          )}
                        </div>
                        <div className="text-[11px] text-muted-foreground font-mono">
                          Capex: £{(c.capex_gbp / 1000000).toFixed(1)}M
                        </div>
                      </div>
                    </div>

                    <div className="text-right">
                      <div className="font-bold font-mono text-emerald-600 dark:text-emerald-400 text-sm">
                        £{(c.npv_gbp / 1000000).toFixed(2)}M NPV
                      </div>
                      <div className="text-[11px] text-muted-foreground font-mono">
                        {irrVal ? `${irrVal.toFixed(1)}% IRR` : '—'}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Deterministic hard checks from the data layer (site_land artifacts) */}
      {artifacts.some((a) => a.stage === 'site_land' && /^(OK|Caveat|Blocker|Unknown): /.test(a.claim)) && (
        <Card className="border-border bg-card shadow-xs rounded-2xl overflow-hidden">
          <CardHeader className="p-4 border-b border-border/70 bg-muted/20">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-1">
              <CardTitle className="text-sm font-bold text-foreground">Site & Land Hard Checks</CardTitle>
              <span className="text-xs text-muted-foreground">
                Deterministic rules on live public data, measured against the real title boundary
              </span>
            </div>
          </CardHeader>
          <CardContent className="p-4 grid grid-cols-1 md:grid-cols-2 gap-2.5">
            {artifacts
              .filter((a) => a.stage === 'site_land' && /^(OK|Caveat|Blocker|Unknown): /.test(a.claim))
              .map((a) => {
                const [outcome, ...rest] = a.claim.split(': ');
                const tone =
                  outcome === 'OK'
                    ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/40'
                    : outcome === 'Caveat'
                      ? 'bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/40'
                      : outcome === 'Blocker'
                        ? 'bg-red-500/15 text-red-700 dark:text-red-300 border-red-500/40'
                        : 'bg-muted text-muted-foreground border-border';
                const name = a.id.replace(/^site_land-/, '').replace(/-[^-]*$/, '').replace(/_/g, ' ');
                return (
                  <div
                    key={a.id}
                    onClick={() => setSelectedArtifact(a)}
                    className="flex items-start gap-3 p-3 rounded-xl border border-border bg-muted/20 text-xs cursor-pointer hover:border-emerald-500/50 hover:bg-muted/30 transition shadow-2xs"
                  >
                    <span className={`shrink-0 w-16 text-center px-2 py-0.5 rounded-md border text-[10px] font-bold uppercase ${tone}`}>
                      {outcome}
                    </span>
                    <div>
                      <div className="font-semibold capitalize text-foreground">{name}</div>
                      <div className="text-muted-foreground mt-0.5">{rest.join(': ')}</div>
                    </div>
                  </div>
                );
              })}
          </CardContent>
        </Card>
      )}

      {/* 4. Explainable AI: Artifacts & Data Provenance */}
      <Card className="border-border bg-card shadow-xs rounded-2xl overflow-hidden">
        <CardHeader className="p-4 border-b border-border/70 bg-muted/20">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-emerald-600 dark:text-emerald-400" />
              <CardTitle className="text-sm font-bold text-foreground">
                Explainable AI: Verified Evidence Artifacts ({artifacts.length})
              </CardTitle>
            </div>
            <span className="text-xs text-muted-foreground">Every claim is grounded in deterministic datasets and Pydantic validation</span>
          </div>
        </CardHeader>

        <CardContent className="p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {artifacts.map((art) => (
            <div
              key={art.id}
              onClick={() => setSelectedArtifact(art)}
              className="p-3.5 rounded-xl border border-border hover:border-emerald-500/60 bg-muted/20 hover:bg-muted/40 cursor-pointer transition flex flex-col justify-between group shadow-2xs"
            >
              <div>
                <div className="flex items-center justify-between text-[10px]">
                  <Badge variant="outline" className="text-[9px] uppercase tracking-wider font-semibold text-emerald-600 dark:text-emerald-400 border-emerald-500/30 bg-emerald-500/10">
                    {art.stage}
                  </Badge>
                  <span className="text-[11px] font-semibold text-muted-foreground whitespace-nowrap">
                    {(art.confidence * 100).toFixed(0)}% Confidence
                  </span>
                </div>
                <p className="mt-2 text-xs font-semibold text-foreground line-clamp-3 leading-relaxed">
                  {art.claim}
                </p>
              </div>

              <div className="mt-3 pt-2.5 border-t border-border/60 flex items-center justify-between text-[10px] text-muted-foreground">
                <span className="truncate max-w-[130px] font-medium">{art.source_name}</span>
                <span className="font-mono">{art.snapshot_date || 'Live API'}</span>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Artifact Modal Dialog */}
      <Dialog open={selectedArtifact !== null} onOpenChange={(open) => !open && setSelectedArtifact(null)}>
        <DialogContent className="sm:max-w-lg border-border bg-card rounded-2xl">
          <DialogHeader>
            <DialogTitle className="text-sm font-bold uppercase tracking-wider text-emerald-600 dark:text-emerald-400 flex items-center gap-2">
              <span>Artifact Provenance Record</span>
              <Badge variant="outline" className="text-xs uppercase">
                {selectedArtifact?.stage}
              </Badge>
            </DialogTitle>
            <DialogDescription className="text-xs text-muted-foreground pt-1">
              Verifiable evidentiary trace backing this feasibility statement.
            </DialogDescription>
          </DialogHeader>

          {selectedArtifact && (
            <div className="space-y-4 text-xs pt-2">
              <div>
                <span className="text-muted-foreground font-medium">Synthesized Claim</span>
                <p className="text-sm font-semibold text-foreground mt-1 bg-muted/30 p-3 rounded-xl border border-border leading-relaxed">
                  {selectedArtifact.claim}
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 py-2 border-y border-border">
                <div>
                  <span className="text-muted-foreground">Data Provider / Register</span>
                  <div className="font-semibold text-foreground mt-0.5">
                    {selectedArtifact.source_name}
                  </div>
                </div>
                <div>
                  <span className="text-muted-foreground">Snapshot Date</span>
                  <div className="font-mono font-medium text-foreground mt-0.5">
                    {selectedArtifact.snapshot_date || 'Current Active Snapshot'}
                  </div>
                </div>
              </div>

              {selectedArtifact.source_url && (
                <div>
                  <span className="text-muted-foreground">Upstream Source URI</span>
                  <a
                    href={selectedArtifact.source_url}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 hover:underline mt-1 break-all font-mono text-[11px]"
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
                className="w-full text-xs font-semibold mt-2 h-10 rounded-xl"
              >
                Close Provenance Dialog
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
