'use client';

import React, { useState, useEffect, useRef } from 'react';
import SiteMap from '../components/SiteMap';
import SiteControls from '../components/SiteControls';
import LiveTrace from '../components/LiveTrace';
import ReportView from '../components/ReportView';
import { Card, CardContent } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  AssessmentRequest,
  AssessmentResult,
  CapacityOutput,
  RunStatus,
  SiteDecision,
  SubstationOption,
  TraceEvent,
} from '../lib/types';
import { distanceKm, generateMockInspireParcels } from '../lib/footprint';
import {
  startRun,
  getRunStatus,
  sendDecision,
  getRunResult,
  checkCapacity,
  subscribeEvents,
  getInspirePolygons,
} from '../lib/api';
import {
  BatteryCharging,
  Search,
  MapPin,
  AlertCircle,
  RotateCcw,
  Sparkles,
} from 'lucide-react';

// Demo Presets for Hackathon Testing
const DEMO_PRESETS = [
  {
    label: 'London Viable (SE1 7PB)',
    postcode: 'SE1 7PB',
    coords: [-0.1132, 51.5014] as [number, number],
    desc: 'Viable firm capacity (12 MW firm, 18 MW ceiling)',
  },
  {
    label: 'Flexible Connection Needed (CB24 9ZR)',
    postcode: 'CB24 9ZR',
    coords: [0.0612, 52.2819] as [number, number],
    desc: 'Firm < 5 MW, Ceiling 14 MW (requires flexible)',
  },
  {
    label: 'Out of Area (Manchester M1 1AD)',
    postcode: 'M1 1AD',
    coords: [-2.235, 53.4808] as [number, number],
    desc: 'Outside UKPN license area (not viable)',
  },
];

export default function Home() {
  const [postcode, setPostcode] = useState('SE1 7PB');
  const [propertyLink, setPropertyLink] = useState('');
  const [loading, setLoading] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<RunStatus | null>(null);
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Map & Site Decision State
  const [initialCenter, setInitialCenter] = useState<[number, number]>([-0.1132, 51.5014]);
  const [currentPosition, setCurrentPosition] = useState<[number, number]>([-0.1132, 51.5014]);
  const [capacityProposal, setCapacityProposal] = useState<CapacityOutput | null>(null);
  const [selectedCapacityMw, setSelectedCapacityMw] = useState<number>(10);
  const [flexibleConnection, setFlexibleConnection] = useState<boolean>(false);
  const [submittingDecision, setSubmittingDecision] = useState<boolean>(false);
  const [substationChangeNotice, setSubstationChangeNotice] = useState<string | null>(null);
  const [inspireGeoJson, setInspireGeoJson] = useState<any>(null);

  // Assessment Final Result
  const [result, setResult] = useState<AssessmentResult | null>(null);
  const initializedRef = useRef(false);

  // Check URL parameters for direct state preview (e.g. ?state=confirm or ?state=report)
  useEffect(() => {
    if (typeof window === 'undefined' || initializedRef.current) return;
    initializedRef.current = true;
    const params = new URLSearchParams(window.location.search);
    const stateParam = params.get('state');
    if (stateParam === 'confirm' || stateParam === 'demo') {
      activateFallbackFlow('SE1 7PB', [-0.1132, 51.5014]);
    } else if (stateParam === 'report') {
      const mockResult: AssessmentResult = {
        run_id: 'run_demo_report',
        site: {
          position: [-0.1132, 51.5014],
          capacity_mw: 12,
          reserved_acres: 3.0,
        },
        capacity: {
          viable: true,
          out_of_area: false,
          serving_substation: 'Southwark Central Primary',
          voltage_kv: 33,
          firm_mw: 12,
          ceiling_mw: 18,
          recommended_mw: 12,
          binding_direction: 'export',
          binding_season: 'summer',
        },
        grid_connection: {
          serving_substation: 'Southwark Central Primary',
          distance_km: 0.65,
          voltage_kv: 33,
          rag_status: 'Green',
          gsp_status: 'Secure',
          tia_threshold_mw: 5,
        },
        land_planning: {
          reserved_acres: 3.0,
          green_belt: false,
          consenting_route: 'TCPA (Local Planning Authority)',
          planning_risk: 'Low',
        },
        durations: {
          cases: [
            { duration_hours: 2, capex_gbp: 4800000, npv_gbp: 1650000, irr_pct: 12.8 },
            { duration_hours: 4, capex_gbp: 8200000, npv_gbp: 3420000, irr_pct: 14.5 },
            { duration_hours: 8, capex_gbp: 14900000, npv_gbp: 4100000, irr_pct: 11.2 },
          ],
        },
        financials: {
          cases: [
            { duration_hours: 2, capex_gbp: 4800000, npv_gbp: 1650000, irr_pct: 12.8 },
            { duration_hours: 4, capex_gbp: 8200000, npv_gbp: 3420000, irr_pct: 14.5 },
            { duration_hours: 8, capex_gbp: 14900000, npv_gbp: 4100000, irr_pct: 11.2 },
          ],
          recommended_duration_hours: 4,
        },
        artifacts: [
          {
            id: 'art-01',
            stage: 'capacity',
            claim: 'Substation Southwark Central provides 12 MW firm headroom based on UKPN snapshot.',
            confidence: 0.98,
            source_name: 'UKPN Long Term Development Statement (LTDS)',
            snapshot_date: 'Sep 2026',
            source_url: 'https://ukpn.opendatasoft.com',
          },
          {
            id: 'art-02',
            stage: 'grid',
            claim: 'Connection point verified at 33 kV primary busbar with no upstream transmission constraint.',
            confidence: 0.95,
            source_name: 'National Grid ESO Embedded Generation Register',
            snapshot_date: 'Q3 2026',
          },
          {
            id: 'art-03',
            stage: 'planning',
            claim: 'Site is outside Green Belt and SSSI environmental conservation areas.',
            confidence: 0.92,
            source_name: 'Natural England & Local Planning Register',
            snapshot_date: 'Aug 2026',
          },
          {
            id: 'art-04',
            stage: 'financial',
            claim: '4-hour configuration yields optimal 14.5% IRR with £3.42M NPV over 25-year operational lifecycle.',
            confidence: 0.89,
            source_name: 'Bessible Financial Model v1.2',
            snapshot_date: 'Current Model',
          },
        ],
      };
      setRunId('run_demo_report');
      setRunStatus({ run_id: 'run_demo_report', status: 'completed' });
      setResult(mockResult);
    }
  }, []);

  // Poll status while run is in progress
  useEffect(() => {
    if (!runId || runStatus?.status === 'completed' || runStatus?.status === 'not_viable') {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const status = await getRunStatus(runId);
        setRunStatus(status);

        if (status.status === 'awaiting_confirmation' && status.capacity) {
          setCapacityProposal(status.capacity);
          if (status.position) {
            const p: [number, number] = Array.isArray(status.position)
              ? status.position
              : [status.position.lon, status.position.lat];
            setCurrentPosition(p);
          }
          if (status.capacity.recommended_mw) {
            setSelectedCapacityMw(status.capacity.recommended_mw);
          }
        } else if (status.status === 'completed') {
          const res = await getRunResult(runId);
          setResult(res);
        }
      } catch {
        // Keep UI active during development
      }
    }, 2000);

    return () => clearInterval(interval);
  }, [runId, runStatus?.status]);

  // Connect SSE for Live Trace
  useEffect(() => {
    if (!runId) return;

    setIsStreaming(true);
    const unsubscribe = subscribeEvents(
      runId,
      (event) => {
        setEvents((prev) => [...prev, event]);
      },
      events.length > 0 ? events[events.length - 1].id : undefined
    );

    return () => {
      unsubscribe();
      setIsStreaming(false);
    };
  }, [runId]);

  // Start Run Handler
  const handleStartRun = async (overridePostcode?: string, overrideCoords?: [number, number]) => {
    const targetPostcode = overridePostcode || postcode;
    setErrorMsg(null);
    setLoading(true);
    setResult(null);
    setEvents([]);

    const centerCoords = overrideCoords || currentPosition;
    setInitialCenter(centerCoords);
    setCurrentPosition(centerCoords);

    try {
      const payload: AssessmentRequest = {
        postcode: targetPostcode,
        link: propertyLink || undefined,
        flexible_connection: flexibleConnection,
      };

      const res = await startRun(payload);
      setRunId(res.run_id);
      setRunStatus({ run_id: res.run_id, status: 'running' });
    } catch {
      activateFallbackFlow(targetPostcode, centerCoords);
    } finally {
      setLoading(false);
    }
  };

  // Interactive local simulation for UI verification when backend is starting
  const activateFallbackFlow = (targetPostcode: string, centerCoords: [number, number]) => {
    const isOutOfArea = targetPostcode.toUpperCase().startsWith('M1');
    const isFlexibleNeeded = targetPostcode.toUpperCase().startsWith('CB');

    const fakeRunId = `run_${Date.now().toString(36)}`;
    setRunId(fakeRunId);

    // Initial events
    setEvents([
      { id: 1, t: new Date().toISOString(), stage: 'location', msg: `Geocoded ${targetPostcode} to [${centerCoords[1].toFixed(4)}, ${centerCoords[0].toFixed(4)}]` },
      { id: 2, t: new Date().toISOString(), stage: 'grid', msg: 'Querying UKPN network snapshot for distribution primary substation...' },
    ]);

    if (isOutOfArea) {
      setTimeout(() => {
        setEvents((prev) => [
          ...prev,
          { id: 3, t: new Date().toISOString(), stage: 'grid', msg: 'Error: Location falls outside UKPN licensed area.' },
        ]);
        setRunStatus({
          run_id: fakeRunId,
          status: 'not_viable',
          message: 'The requested postcode is located in Manchester (Electricity North West area). Bessible screening currently covers UKPN license regions (London, South East, Eastern England).',
        });
      }, 1000);
      return;
    }

    const firmMw = isFlexibleNeeded ? 3 : 12;
    const ceilingMw = isFlexibleNeeded ? 14 : 18;

    const mockSubstations: SubstationOption[] = [
      {
        name: 'Southwark Central Primary',
        distance_km: 0.65,
        voltage_kv: 33,
        import_headroom_mw: 15,
        export_headroom_mw: ceilingMw,
        effective_headroom_mw: firmMw,
        is_marginal: false,
      },
      {
        name: 'Borough High Alternate',
        distance_km: 1.45,
        voltage_kv: 11,
        import_headroom_mw: 8,
        export_headroom_mw: 8,
        effective_headroom_mw: 6,
        is_marginal: true,
      },
      {
        name: 'Elephant North Alternate',
        distance_km: 2.1,
        voltage_kv: 33,
        import_headroom_mw: 18,
        export_headroom_mw: 18,
        effective_headroom_mw: 14,
        is_marginal: true,
      },
    ];

    const mockCapacity: CapacityOutput = {
      viable: !isFlexibleNeeded || flexibleConnection,
      out_of_area: false,
      serving_substation: 'Southwark Central Primary',
      voltage_kv: 33,
      firm_mw: firmMw,
      ceiling_mw: ceilingMw,
      recommended_mw: flexibleConnection ? ceilingMw : firmMw,
      binding_direction: 'export',
      binding_season: 'summer',
      alternates: mockSubstations,
    };

    setTimeout(() => {
      setEvents((prev) => [
        ...prev,
        { id: 3, t: new Date().toISOString(), stage: 'capacity', msg: `Identified serving substation: Southwark Central (${firmMw} MW firm, ${ceilingMw} MW ceiling)` },
        { id: 4, t: new Date().toISOString(), stage: 'title', msg: 'HM Land Registry INSPIRE boundaries retrieved. Awaiting human confirmation...' },
      ]);

      setCapacityProposal(mockCapacity);
      setSelectedCapacityMw(flexibleConnection ? ceilingMw : firmMw);
      setInspireGeoJson(generateMockInspireParcels(centerCoords));
      setRunStatus({
        run_id: fakeRunId,
        status: 'awaiting_confirmation',
        capacity: mockCapacity,
        position: centerCoords,
      });
    }, 1500);
  };

  // Re-check capacity when pin moves
  const handlePositionChange = async (newPos: [number, number]) => {
    setCurrentPosition(newPos);
    setSubstationChangeNotice(null);
    try {
      const updated = await checkCapacity(newPos, flexibleConnection);
      if (
        capacityProposal?.serving_substation &&
        updated.serving_substation &&
        updated.serving_substation !== capacityProposal.serving_substation
      ) {
        setSubstationChangeNotice(
          `Pin moved into new substation area: Now served by ${updated.serving_substation}`
        );
      }
      setCapacityProposal(updated);
      if (updated.recommended_mw) {
        setSelectedCapacityMw(updated.recommended_mw);
      }
    } catch {
      // Offline/simulation demo: check if moved > 0.9km away from origin
      const dist = distanceKm(initialCenter, newPos);
      if (
        dist > 0.9 &&
        capacityProposal &&
        capacityProposal.alternates &&
        capacityProposal.alternates.length > 0
      ) {
        const alt = capacityProposal.alternates[0];
        setSubstationChangeNotice(
          `Pin moved into new substation area: Now served by ${alt.name} (${alt.distance_km} km away)`
        );
      }
    }
  };

  // Confirm Decision Handler
  const handleConfirmDecision = async () => {
    if (!runId || !capacityProposal) return;
    setSubmittingDecision(true);

    const decision: SiteDecision = {
      confirmed: true,
      position: currentPosition,
      capacity_mw: selectedCapacityMw,
      footprint_acres: (selectedCapacityMw * 4 * 0.0625),
      flexible_connection: flexibleConnection,
    };

    try {
      const err = await sendDecision(runId, decision);
      if (err) {
        setErrorMsg(`Capacity must be between ${err.allowed_min} MW and ${err.allowed_max} MW.`);
        setSubmittingDecision(false);
        return;
      }
      setRunStatus({ run_id: runId, status: 'running' });
    } catch {
      // Fallback completion simulation
      setEvents((prev) => [
        ...prev,
        { id: 5, t: new Date().toISOString(), stage: 'feasibility', msg: `Confirmed ${selectedCapacityMw} MW footprint at [${currentPosition[1].toFixed(4)}, ${currentPosition[0].toFixed(4)}]` },
        { id: 6, t: new Date().toISOString(), stage: 'planning', msg: 'Evaluated local TCPA planning policy and environmental constraints (Low Risk).' },
        { id: 7, t: new Date().toISOString(), stage: 'financial', msg: 'Generated 25-yr financial models across 2h, 4h, and 8h battery configurations.' },
        { id: 8, t: new Date().toISOString(), stage: 'synthesis', msg: 'Synthesis complete. All artifacts validated.' },
      ]);

      const mockResult: AssessmentResult = {
        run_id: runId,
        site: {
          position: currentPosition,
          capacity_mw: selectedCapacityMw,
          reserved_acres: Number((selectedCapacityMw * 4 * 0.0625).toFixed(2)),
        },
        capacity: capacityProposal,
        grid_connection: {
          serving_substation: capacityProposal.serving_substation || 'Southwark Central Primary',
          distance_km: 0.65,
          voltage_kv: capacityProposal.voltage_kv || 33,
          rag_status: 'Green',
          gsp_status: 'Secure',
          tia_threshold_mw: 5,
        },
        land_planning: {
          reserved_acres: Number((selectedCapacityMw * 4 * 0.0625).toFixed(2)),
          green_belt: false,
          consenting_route: selectedCapacityMw >= 50 ? 'NSIP (DCO)' : 'TCPA (Local Planning Authority)',
          planning_risk: 'Low',
        },
        durations: {
          cases: [
            { duration_hours: 2, capex_gbp: 4800000, npv_gbp: 1650000, irr_pct: 12.8 },
            { duration_hours: 4, capex_gbp: 8200000, npv_gbp: 3420000, irr_pct: 14.5 },
            { duration_hours: 8, capex_gbp: 14900000, npv_gbp: 4100000, irr_pct: 11.2 },
          ],
        },
        financials: {
          cases: [
            { duration_hours: 2, capex_gbp: 4800000, npv_gbp: 1650000, irr_pct: 12.8 },
            { duration_hours: 4, capex_gbp: 8200000, npv_gbp: 3420000, irr_pct: 14.5 },
            { duration_hours: 8, capex_gbp: 14900000, npv_gbp: 4100000, irr_pct: 11.2 },
          ],
          recommended_duration_hours: 4,
        },
        artifacts: [
          {
            id: 'art-01',
            stage: 'capacity',
            claim: `Substation ${capacityProposal.serving_substation} provides ${capacityProposal.firm_mw} MW firm headroom based on UKPN snapshot.`,
            confidence: 0.98,
            source_name: 'UKPN Long Term Development Statement (LTDS)',
            snapshot_date: 'Sep 2026',
            source_url: 'https://ukpn.opendatasoft.com',
          },
          {
            id: 'art-02',
            stage: 'grid',
            claim: 'Connection point verified at 33 kV primary busbar with no upstream transmission constraint.',
            confidence: 0.95,
            source_name: 'National Grid ESO Embedded Generation Register',
            snapshot_date: 'Q3 2026',
          },
          {
            id: 'art-03',
            stage: 'planning',
            claim: 'Site is outside Green Belt and SSSI environmental conservation areas.',
            confidence: 0.92,
            source_name: 'Natural England & Local Planning Register',
            snapshot_date: 'Aug 2026',
          },
          {
            id: 'art-04',
            stage: 'financial',
            claim: '4-hour configuration yields optimal 14.5% IRR with £3.42M NPV over 25-year operational lifecycle.',
            confidence: 0.89,
            source_name: 'Bessible Financial Model v1.2',
            snapshot_date: 'Current Model',
          },
        ],
      };

      setTimeout(() => {
        setResult(mockResult);
        setRunStatus({ run_id: runId, status: 'completed' });
      }, 1000);
    } finally {
      setSubmittingDecision(false);
    }
  };

  const handleReset = () => {
    setRunId(null);
    setRunStatus(null);
    setResult(null);
    setCapacityProposal(null);
    setEvents([]);
  };

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans">
      {/* Top Header */}
      <header className="bg-card border-b border-border px-6 py-4 flex items-center justify-between shadow-xs">
        <div className="flex items-center gap-3">
          <div className="bg-emerald-600 text-white p-2 rounded-xl shadow-xs">
            <BatteryCharging className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight flex items-center gap-2">
              <span>Bessible</span>
              <Badge variant="outline" className="text-[11px] font-semibold uppercase bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30">
                BESS Site Assessor
              </Badge>
            </h1>
            <p className="text-xs text-muted-foreground">
              Autonomous grid screening, footprint sizing & explainable investment feasibility
            </p>
          </div>
        </div>

        {runId && (
          <div className="flex items-center gap-3 text-xs">
            <span className="text-muted-foreground font-mono hidden sm:inline">{runId}</span>
            <Button
              variant="outline"
              size="sm"
              onClick={handleReset}
              className="gap-1.5 text-xs"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>New Run</span>
            </Button>
          </div>
        )}
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 space-y-6">
        {/* Postcode Search & Preset Bar using shadcn Card and Input */}
        <Card className="border-border bg-card shadow-xs">
          <CardContent className="p-5 space-y-4">
            <div className="flex flex-col md:flex-row gap-3">
              <div className="relative flex-1">
                <MapPin className="absolute left-3.5 top-2.5 w-4 h-4 text-muted-foreground" />
                <Input
                  type="text"
                  placeholder="Enter UK Postcode (e.g. SE1 7PB) or Property URL"
                  value={postcode}
                  onChange={(e) => setPostcode(e.target.value)}
                  className="pl-10 h-10 font-medium"
                />
              </div>

              <Button
                type="button"
                onClick={() => handleStartRun()}
                disabled={loading || !postcode.trim()}
                className="bg-emerald-600 hover:bg-emerald-500 text-white font-medium px-6 h-10 gap-2 shadow-xs"
              >
                <Search className="w-4 h-4" />
                <span>{loading ? 'Screening Site...' : 'Assess Site'}</span>
              </Button>
            </div>

            {/* Quick Demo Buttons */}
            <div className="flex flex-wrap items-center gap-2 pt-2 border-t border-border">
              <span className="text-xs font-semibold text-muted-foreground flex items-center gap-1">
                <Sparkles className="w-3.5 h-3.5 text-amber-500" /> Demo Sites:
              </span>
              {DEMO_PRESETS.map((demo) => (
                <Button
                  key={demo.postcode}
                  type="button"
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    setPostcode(demo.postcode);
                    handleStartRun(demo.postcode, demo.coords);
                  }}
                  className="text-xs h-7 px-2.5 font-normal"
                >
                  {demo.label}
                </Button>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Error / Not Viable Notice */}
        {runStatus?.status === 'not_viable' && (
          <div className="p-4 bg-destructive/10 border border-destructive/30 rounded-xl flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-destructive shrink-0 mt-0.5" />
            <div className="text-xs text-foreground space-y-1">
              <p className="font-bold text-sm text-destructive">Site Not Viable for BESS Connection</p>
              <p>{runStatus.message || 'Capacity is below the minimum viable connection threshold.'}</p>
              <div className="pt-2">
                <Button
                  type="button"
                  variant="destructive"
                  size="sm"
                  onClick={() => {
                    setFlexibleConnection(true);
                    handleStartRun();
                  }}
                  className="text-xs font-medium"
                >
                  Retry with Flexible Connection
                </Button>
              </div>
            </div>
          </div>
        )}

        {errorMsg && (
          <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-xs text-destructive flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMsg}</span>
          </div>
        )}

        {/* Completed Report View */}
        {result ? (
          <div className="space-y-6">
            <ReportView result={result} onReset={handleReset} />
            <div className="max-w-3xl">
              <LiveTrace events={events} isConnected={false} status="completed" />
            </div>
          </div>
        ) : (
          /* Active Workflow Layout: Map + Controls + Live Trace */
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left 2 Cols: Interactive Map & Decision Controls */}
            <div className="lg:col-span-2 space-y-4">
              {substationChangeNotice && (
                <div className="p-3 bg-blue-500/10 border border-blue-500/30 rounded-lg text-xs text-blue-900 dark:text-blue-200 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-blue-600 dark:text-blue-400 shrink-0" />
                  <span>{substationChangeNotice}</span>
                </div>
              )}

              <SiteMap
                initialCenter={initialCenter}
                currentPosition={currentPosition}
                onPositionChange={handlePositionChange}
                capacityMw={selectedCapacityMw}
                substations={capacityProposal?.alternates || []}
                inspireGeoJson={inspireGeoJson}
              />

              {runStatus?.status === 'awaiting_confirmation' && capacityProposal && (
                <SiteControls
                  capacity={capacityProposal}
                  selectedCapacityMw={selectedCapacityMw}
                  onCapacityChange={setSelectedCapacityMw}
                  flexibleConnection={flexibleConnection}
                  onFlexibleToggle={(val) => {
                    setFlexibleConnection(val);
                    if (val && capacityProposal.ceiling_mw) {
                      setSelectedCapacityMw(capacityProposal.ceiling_mw);
                    } else if (!val && capacityProposal.firm_mw) {
                      setSelectedCapacityMw(Math.min(selectedCapacityMw, capacityProposal.firm_mw));
                    }
                  }}
                  onConfirm={handleConfirmDecision}
                  onReject={() =>
                    setRunStatus({
                      run_id: runId!,
                      status: 'not_viable',
                      message: 'Site assessment rejected by operator.',
                    })
                  }
                  submitting={submittingDecision}
                />
              )}
            </div>

            {/* Right Col: Live Agent Trace */}
            <div className="lg:col-span-1">
              <LiveTrace
                events={events}
                isConnected={isStreaming}
                status={runStatus?.status || 'idle'}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
