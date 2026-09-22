'use client';

import React, { useState, useEffect, useRef } from 'react';
import SiteMap from '../components/SiteMap';
import SiteControls from '../components/SiteControls';
import LiveTrace from '../components/LiveTrace';
import ReportView from '../components/ReportView';
import KeyPanel from '../components/KeyPanel';
import FirstLoadModal from '../components/FirstLoadModal';
import SignedOutLanding from '../components/SignedOutLanding';
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
  getSiteData,
  getKeyStatus,
  startDemoRun,
  isDemoRun,
  ApiError,
  KeyStatus,
} from '../lib/api';
import { useAuth } from '../lib/auth';
import {
  Search,
  MapPin,
  AlertCircle,
  RotateCcw,
  Sparkles,
  Settings,
  LogIn,
  LogOut,
  PlayCircle,
  Film,
  ChevronDown,
} from 'lucide-react';

// Demo Presets for Hackathon Testing
const DEMO_PRESETS = [
  {
    label: 'Dorking Viable (RH4 1AD)',
    postcode: 'RH4 1AD',
    coords: [-0.3302, 51.2329] as [number, number],
    desc: 'Viable firm capacity (8 MW firm at Dorking Town 11kV)',
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
  const auth = useAuth();
  const [postcode, setPostcode] = useState('SE1 7PB');
  const [propertyLink, setPropertyLink] = useState('');
  const [loading, setLoading] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [runStatus, setRunStatus] = useState<RunStatus | null>(null);
  const [events, setEvents] = useState<TraceEvent[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Map & Site Decision State
  const positionedRunRef = useRef<string | null>(null);
  const pendingPinRef = useRef<[number, number] | null>(null);
  const lastRunPostcodeRef = useRef<string | null>(null);
  const proposedRunRef = useRef<string | null>(null);
  const [initialCenter, setInitialCenter] = useState<[number, number]>([-0.1132, 51.5014]);
  const [currentPosition, setCurrentPosition] = useState<[number, number]>([-0.1132, 51.5014]);
  const [capacityProposal, setCapacityProposal] = useState<CapacityOutput | null>(null);
  const [capacityLoading, setCapacityLoading] = useState(false);
  const [selectedCapacityMw, setSelectedCapacityMw] = useState<number>(10);
  const [flexibleConnection, setFlexibleConnection] = useState<boolean>(false);
  const [submittingDecision, setSubmittingDecision] = useState<boolean>(false);
  const [substationChangeNotice, setSubstationChangeNotice] = useState<string | null>(null);
  const [inspireGeoJson, setInspireGeoJson] = useState<GeoJSON.GeoJSON | null>(null);
  const [siteData, setSiteData] = useState<any>(null);
  const [siteDataLoading, setSiteDataLoading] = useState(false);

  // Google key (BYOK): loaded once the user is signed in. Local mode (no Firebase config) skips all of this.
  const [keyState, setKeyState] = useState<{ uid: string; status: KeyStatus } | null>(null);
  const [keyPanelOpen, setKeyPanelOpen] = useState(false);
  const [welcomeDismissed, setWelcomeDismissed] = useState(false);
  const [signInError, setSignInError] = useState<string | null>(null);
  const [signingIn, setSigningIn] = useState(false);
  const signedInUid = auth.user?.uid;
  // Key state is tagged with its owner so a previous user's key never shows for the next sign-in.
  const currentKeyStatus = keyState && keyState.uid === signedInUid ? keyState.status : null;
  const setKeyStatus = (status: KeyStatus) => {
    if (signedInUid) setKeyState({ uid: signedInUid, status });
  };

  useEffect(() => {
    if (!signedInUid) return;
    let stale = false;
    getKeyStatus()
      .then((status) => !stale && setKeyState({ uid: signedInUid, status }))
      .catch(
        () =>
          !stale && setKeyState({ uid: signedInUid, status: { configured: false, last4: null, updated_at: null } })
      );
    return () => {
      stale = true;
    };
  }, [signedInUid]);

  // Real data for wherever the pin is: coordinate -> location.collate -> LocationData
  useEffect(() => {
    const [lon, lat] = currentPosition;
    if (lon === -0.1132 && lat === 51.5014) return; // untouched default
    let stale = false;
    const timer = setTimeout(async () => {
      setSiteDataLoading(true);
      try {
        const data = await getSiteData(lat, lon);
        if (!stale && data) setSiteData(data);
      } catch {
        // keep the last layer
      } finally {
        if (!stale) setSiteDataLoading(false);
      }
    }, 400);
    return () => {
      stale = true;
      clearTimeout(timer);
    };
  }, [currentPosition]);

  // Assessment Final Result
  const [result, setResult] = useState<AssessmentResult | null>(null);
  const initializedRef = useRef(false);

  // Interactive local simulation for UI verification when backend is starting
  const activateFallbackFlow = (
    targetPostcode: string,
    centerCoords: [number, number],
    immediate: boolean = false
  ) => {
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
        setCapacityLoading(false);
      }, immediate ? 0 : 1000);
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

    const applyReady = () => {
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
      setCapacityLoading(false);
    };

    if (immediate) {
      applyReady();
    } else {
      setTimeout(applyReady, 1200);
    }
  };

  // Check URL parameters for direct state preview (e.g. ?state=confirm or ?state=report)
  useEffect(() => {
    if (typeof window === 'undefined' || initializedRef.current) return;
    initializedRef.current = true;
    const params = new URLSearchParams(window.location.search);
    const stateParam = params.get('state');
    if (stateParam === 'confirm' || stateParam === 'demo') {
      activateFallbackFlow('SE1 7PB', [-0.1132, 51.5014], true);
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
        if (status.status !== 'running') {
          setCapacityLoading(false);
        }

        if (status.position && positionedRunRef.current !== runId) {
          positionedRunRef.current = runId;
          const p: [number, number] = Array.isArray(status.position)
            ? status.position
            : [status.position.lon, status.position.lat];
          setInitialCenter(p);
          setCurrentPosition(pendingPinRef.current ?? p);
        }
        if (status.status === 'awaiting_confirmation' && status.capacity && proposedRunRef.current !== runId) {
          proposedRunRef.current = runId;
          setCapacityProposal(status.capacity);
          if (status.capacity.recommended_mw) {
            setSelectedCapacityMw(status.capacity.recommended_mw);
          }
          if (pendingPinRef.current) {
            const pin = pendingPinRef.current;
            pendingPinRef.current = null;
            void handlePositionChange(pin);
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
  const handleStartRun = async (
    overridePostcode?: string,
    overrideCoords?: [number, number],
    overrideFlexible?: boolean
  ) => {
    if (auth.enabled && !auth.user) {
      setErrorMsg('Sign in to run a real assessment, or keep exploring the recorded example.');
      return;
    }
    const targetInput = (overridePostcode || postcode).trim();
    const isUrl = targetInput.startsWith('http://') || targetInput.startsWith('https://');
    let targetPostcode = isUrl ? 'SE1 7PB' : targetInput;
    const flexible = overrideFlexible ?? flexibleConnection;

    // Pin dragged away from the last assessed postcode (and the postcode text untouched): assess where the pin is.
    // A run starts from a postcode, so use the nearest one and keep the pin where the user put it.
    pendingPinRef.current = null;
    const pinMoved = distanceKm(initialCenter, currentPosition) > 0.05;
    if (!overridePostcode && !isUrl && pinMoved && postcode === lastRunPostcodeRef.current) {
      try {
        const r = await fetch(
          `https://api.postcodes.io/postcodes?lon=${currentPosition[0]}&lat=${currentPosition[1]}&limit=1&radius=2000&widesearch=true`
        );
        const nearest = (await r.json())?.result?.[0]?.postcode as string | undefined;
        if (nearest) {
          targetPostcode = nearest;
          setPostcode(nearest);
          pendingPinRef.current = currentPosition;
        }
      } catch {
        // fall through to the typed postcode
      }
    }
    lastRunPostcodeRef.current = targetPostcode;
    setErrorMsg(null);
    setLoading(true);
    setResult(null);
    setEvents([]);
    setRunStatus(null);
    setInspireGeoJson(null);
    setSubstationChangeNotice(null);
    // Keep the previous run's capacity card mounted (SiteControls shows it dimmed, under a
    // loading overlay) instead of unmounting it while the new run's data is in flight.
    setCapacityLoading(true);
    positionedRunRef.current = null;
    proposedRunRef.current = null;

    const centerCoords = overrideCoords || currentPosition;
    setInitialCenter(centerCoords);
    setCurrentPosition(centerCoords);

    try {
      const payload: AssessmentRequest = isUrl
        ? {
            link: targetInput,
            property_url: targetInput,
            flexible_connection: flexible,
          }
        : {
            postcode: targetPostcode,
            link: propertyLink.trim() || undefined,
            flexible_connection: flexible,
          };

      const res = await startRun(payload);
      setRunId(res.run_id);
      setRunStatus({ run_id: res.run_id, status: 'running' });
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setCapacityLoading(false);
        // Auth failures are real: do not hide them behind the offline simulation.
        if (JSON.stringify(err.data).includes('missing_google_key')) {
          setKeyStatus({ configured: false, last4: null, updated_at: null });
          setKeyPanelOpen(true);
          setErrorMsg('Add your Google AI key to start a real assessment.');
        } else {
          setErrorMsg('Your session has expired. Sign in again to continue.');
        }
      } else {
        activateFallbackFlow(targetPostcode, centerCoords);
      }
    } finally {
      setLoading(false);
    }
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

  // Recorded example run: public replay, no sign-in, keys, Temporal or live model calls.
  const handleStartDemo = async () => {
    setKeyPanelOpen(false);
    setErrorMsg(null);
    setLoading(true);
    setResult(null);
    setEvents([]);
    setCapacityProposal(null);
    // Align input and map coordinates to the recorded demo location (Dorking Viable)
    setPostcode('RH4 1AD');
    setInitialCenter([-0.3302, 51.2329]);
    setCurrentPosition([-0.3302, 51.2329]);
    lastRunPostcodeRef.current = 'RH4 1AD';
    try {
      const res = await startDemoRun();
      setRunId(res.run_id);
      setRunStatus({ run_id: res.run_id, status: 'running' });
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Could not start the demo run.');
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setRunId(null);
    setRunStatus(null);
    setResult(null);
    setCapacityProposal(null);
    setCapacityLoading(false);
    setInspireGeoJson(null);
    setSubstationChangeNotice(null);
    setSiteData(null);
    setEvents([]);
    setPostcode('');
    positionedRunRef.current = null;
    proposedRunRef.current = null;
    pendingPinRef.current = null;
    lastRunPostcodeRef.current = null;
    setErrorMsg(null);
  };

  const handleResetRun = () => {
    if (isDemo) {
      void handleStartDemo();
    } else {
      handleReset();
    }
  };

  const handleSignIn = async () => {
    setSigningIn(true);
    setSignInError(null);
    try {
      await auth.signIn();
      // Signing in clears any demo data ready for a fresh authenticated run
      handleReset();
    } catch (err) {
      const code = (err as { code?: string })?.code;
      if (code !== 'auth/popup-closed-by-user' && code !== 'auth/cancelled-popup-request') {
        setSignInError('Sign-in failed. Try again.');
      }
    } finally {
      setSigningIn(false);
    }
  };

  // If the user authenticates while viewing the recorded demo replay, clear demo data for a fresh run
  const prevUserRef = useRef(auth.user);
  useEffect(() => {
    if (!prevUserRef.current && auth.user && isDemoRun(runId)) {
      handleReset();
    }
    prevUserRef.current = auth.user;
  }, [auth.user, runId]);

  const isDemo = isDemoRun(runId);

  if (auth.enabled && auth.loading) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center p-6">
        <div className="flex flex-col items-center gap-3">
          <div className="bg-emerald-600 text-white p-3.5 rounded-2xl shadow-xs animate-pulse">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 -960 960 960"
              width="32"
              height="32"
              fill="currentColor"
              aria-hidden="true"
            >
              <path d="M320-80q-17 0-28.5-11.5T280-120v-640q0-17 11.5-28.5T320-800h80v-80h160v80h80q17 0 28.5 11.5T680-760v280q-100 1-170 70.5T440-240q0 46 16 87t45 73H320Zm40-400h240v-240H360v240ZM660-80v-120H560l140-200v120h100L660-80Z" />
            </svg>
          </div>
          <span className="text-xs text-muted-foreground font-medium animate-pulse">Loading Bessible…</span>
        </div>
      </div>
    );
  }
  // No session: landing page, until the visitor starts the demo replay.
  if (auth.enabled && !auth.user && !isDemo) {
    return (
      <SignedOutLanding
        onSignIn={handleSignIn}
        onViewDemo={handleStartDemo}
        signingIn={signingIn}
        error={signInError ?? errorMsg}
      />
    );
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col font-sans">
      <KeyPanel
        open={keyPanelOpen}
        onOpenChange={setKeyPanelOpen}
        status={currentKeyStatus}
        onStatusChange={setKeyStatus}
      />
      <FirstLoadModal
        open={!!auth.user && currentKeyStatus?.configured === false && !welcomeDismissed && !keyPanelOpen && !isDemo}
        onConfigureKey={() => setKeyPanelOpen(true)}
        onViewDemo={() => {
          setWelcomeDismissed(true);
          void handleStartDemo();
        }}
        onDismiss={() => setWelcomeDismissed(true)}
      />

      {/* Top Header */}
      <header className="bg-card/90 backdrop-blur-md border-b border-border/80 px-6 py-3.5 flex items-center justify-between shadow-xs sticky top-0 z-30">
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={handleReset}
            aria-label="Back to start"
            title="Back to start"
            className="bg-emerald-600 text-white p-2.5 rounded-xl shadow-xs hover:bg-emerald-500 transition-colors cursor-pointer"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 -960 960 960"
              width="20"
              height="20"
              fill="currentColor"
              aria-hidden="true"
            >
              <path d="M320-80q-17 0-28.5-11.5T280-120v-640q0-17 11.5-28.5T320-800h80v-80h160v80h80q17 0 28.5 11.5T680-760v280q-100 1-170 70.5T440-240q0 46 16 87t45 73H320Zm40-400h240v-240H360v240ZM660-80v-120H560l140-200v120h100L660-80Z" />
            </svg>
          </button>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold tracking-tight">Bessible</span>
              <Badge variant="outline" className="text-[10px] font-bold uppercase tracking-wider bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border-emerald-500/30">
                BESS Screening Terminal
              </Badge>
            </div>
            <p className="text-[11px] text-muted-foreground hidden sm:block">
              Autonomous grid screening, footprint sizing & explainable investment feasibility
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden md:flex items-center gap-2 text-[11px] font-mono text-muted-foreground border-r border-border pr-3">
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 font-semibold border border-emerald-500/20">
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
              UKPN Live API
            </span>
            <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-md bg-blue-500/10 text-blue-700 dark:text-blue-300 font-semibold border border-blue-500/20">
              Temporal Engine
            </span>
          </div>

          {isDemo && (
            <Badge variant="outline" className="gap-1 text-[10px] font-bold uppercase tracking-wider bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30">
              <Film className="w-3 h-3" /> Recorded example
            </Badge>
          )}

          {/* Settings & API Key modal trigger - always accessible */}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setKeyPanelOpen(true)}
            className="gap-1.5 text-xs h-8 px-2.5 sm:px-3 rounded-xl border-border cursor-pointer hover:bg-muted/80 transition-colors"
            title="Settings & Google AI Key"
            aria-label="Settings"
          >
            <Settings className="w-3.5 h-3.5 text-muted-foreground" />
            <span className="hidden sm:inline">Settings</span>
            {currentKeyStatus?.configured && (
              <span className="text-[10px] font-mono bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 px-1.5 py-0.5 rounded border border-emerald-500/20">
                ••••{currentKeyStatus.last4}
              </span>
            )}
          </Button>

          {auth.enabled && !auth.user && (
            <Button
              size="sm"
              onClick={handleSignIn}
              disabled={signingIn}
              className="bg-emerald-600 hover:bg-emerald-500 text-white gap-1.5 text-xs h-8 px-3 rounded-xl cursor-pointer shadow-xs"
            >
              <LogIn className="w-3.5 h-3.5" />
              <span>{signingIn ? 'Signing in…' : 'Sign in'}</span>
            </Button>
          )}

          {auth.enabled && auth.user && (
            <div className="flex items-center gap-2 text-xs">
              <span className="text-muted-foreground hidden md:inline max-w-[160px] truncate text-[11px] font-medium" title={auth.user.email ?? undefined}>
                {auth.user.email}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  handleReset();
                  void auth.signOut();
                }}
                className="gap-1.5 text-xs h-8 px-2.5 rounded-xl cursor-pointer text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
                aria-label="Sign out"
                title="Sign out"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">Logout</span>
              </Button>
            </div>
          )}

          {runId && (
            <div className="flex items-center gap-2.5 text-xs">
              <span className="text-muted-foreground font-mono text-[11px] hidden sm:inline bg-muted/50 px-2 py-1 rounded-md border border-border">
                {runId}
              </span>
              <Button
                variant="outline"
                size="sm"
                onClick={handleResetRun}
                className="gap-1.5 text-xs h-8 px-3 rounded-xl border-border cursor-pointer hover:bg-muted/80 transition-colors"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Reset Run</span>
              </Button>
            </div>
          )}
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 max-w-[1800px] w-full mx-auto p-4 sm:p-6 space-y-6">
        {/* Postcode Search & Action Bar */}
        <div className="flex flex-col md:flex-row gap-3">
          <div className="relative flex-1">
            <MapPin className="absolute left-3.5 top-3.5 w-4 h-4 text-emerald-600" />
            <Input
              type="text"
              placeholder={isDemo ? 'Demo Site: RH4 1AD' : 'Enter UK Postcode (e.g. SE1 7PB) or Property URL'}
              value={postcode}
              disabled={isDemo}
              onChange={(e) => setPostcode(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && postcode.trim() && !loading && !isDemo) {
                  handleStartRun();
                }
              }}
              className="pl-10 h-11 font-medium rounded-xl text-sm bg-card shadow-xs border-border disabled:opacity-85 disabled:cursor-not-allowed"
            />
          </div>

          {isDemo ? (
            <div className="relative min-w-[280px]">
              <Sparkles className="absolute left-3.5 top-3.5 w-4 h-4 text-amber-500 pointer-events-none z-10" />
              <select
                aria-label="Select demo site"
                value={DEMO_PRESETS.find((p) => p.postcode === postcode)?.postcode ?? DEMO_PRESETS[0].postcode}
                onChange={(e) => {
                  const preset = DEMO_PRESETS.find((p) => p.postcode === e.target.value);
                  if (preset) {
                    setPostcode(preset.postcode);
                    if (preset.postcode === 'RH4 1AD') {
                      void handleStartDemo();
                    } else {
                      activateFallbackFlow(preset.postcode, preset.coords, true);
                    }
                  }
                }}
                disabled={loading}
                className="w-full h-11 pl-10 pr-9 bg-card border border-border text-foreground font-semibold rounded-xl text-sm shadow-xs appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-emerald-500/30 hover:border-emerald-500/40 transition-colors"
              >
                {DEMO_PRESETS.map((demo) => (
                  <option key={demo.postcode} value={demo.postcode}>
                    {demo.label}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3.5 top-3.5 w-4 h-4 text-muted-foreground pointer-events-none z-10" />
            </div>
          ) : (
            <Button
              type="button"
              onClick={() => handleStartRun()}
              disabled={loading || !postcode.trim()}
              className="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold px-6 h-11 rounded-xl gap-2 shadow-xs cursor-pointer text-sm"
            >
              <Search className="w-4 h-4 stroke-[2.5]" />
              <span>{loading ? 'Screening Grid...' : 'Screen Location'}</span>
            </Button>
          )}
        </div>

        {isDemo && (
          <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg text-xs text-amber-900 dark:text-amber-200 flex items-center gap-2">
            <PlayCircle className="w-4 h-4 shrink-0" />
            <span>
              This is a <strong>recorded example</strong> replayed from a saved run, not live output. Nothing here calls a
              model or uses a key.
            </span>
          </div>
        )}

        {/* Error / Not Viable Notice */}
        {runStatus?.status === 'not_viable' && (
          <div className="p-4 bg-destructive/10 border border-destructive/30 rounded-xl flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-destructive shrink-0 mt-0.5" />
            <div className="text-xs text-foreground space-y-1">
              <p className="font-bold text-sm text-destructive">Site Not Viable for BESS Connection</p>
              <p>
                {runStatus.message ||
                  runStatus.capacity?.message ||
                  'Capacity is below the minimum viable connection threshold.'}
              </p>
              <div
                className="pt-2"
                hidden={flexibleConnection || !/flexible/i.test(runStatus.message || runStatus.capacity?.message || '')}
              >
                <Button
                  type="button"
                  variant="destructive"
                  size="sm"
                  onClick={() => {
                    setFlexibleConnection(true);
                    handleStartRun(undefined, undefined, true);
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
          <div className="p-3 bg-destructive/10 border border-destructive/30 rounded-lg text-xs text-destructive flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMsg}</span>
            </div>
            {auth.enabled && !auth.user && (
              <Button
                size="sm"
                variant="outline"
                onClick={handleSignIn}
                disabled={signingIn}
                className="h-7 text-xs border-destructive/40 text-destructive hover:bg-destructive/10 shrink-0 cursor-pointer"
              >
                Sign in
              </Button>
            )}
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
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
            {/* Left 2 Cols: Interactive Map & Decision Controls */}
            <div className="lg:col-span-3 space-y-4">
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
                substations={capacityLoading ? [] : capacityProposal?.alternates || []}
                inspireGeoJson={inspireGeoJson}
                siteData={siteData}
                siteDataLoading={siteDataLoading}
              />

              {(capacityLoading || runStatus?.status === 'awaiting_confirmation') && capacityProposal && (
                <SiteControls
                  capacity={capacityProposal}
                  loading={capacityLoading}
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
