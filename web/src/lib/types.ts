export interface PositionCoords {
  lat: number;
  lon: number;
}

export interface AssessmentRequest {
  postcode?: string;
  property_url?: string;
  link?: string;
  battery_mw?: number;
  target_mw?: number;
  budget_gbp?: number;
  flexible_connection?: boolean;
}

export interface SubstationOption {
  name: string;
  distance_km: number;
  import_headroom_mw: number;
  export_headroom_mw: number;
  effective_headroom_mw: number;
  voltage_kv: number;
  is_marginal: boolean; // true if distance > 1 km
}

export interface Artifact {
  id: string;
  stage: string;
  claim: string;
  confidence: number;
  source_name?: string;
  model_used?: string;
  source_url?: string;
  file_path?: string;
  image_path?: string;
  snapshot_date?: string;
}

export interface CapacityOutput {
  viable: boolean;
  out_of_area: boolean;
  message?: string;
  substation?: string;
  serving_substation?: string;
  connection_voltage_kv?: number;
  voltage_kv?: number;
  firm_mw?: number;
  ceiling_mw?: number;
  recommended_mw?: number;
  binding_direction?: 'import' | 'export';
  binding_season?: 'winter' | 'summer';
  distance_km?: number;
  alternates?: SubstationOption[];
  artifacts?: Artifact[];
}

export interface ConfirmedSite {
  position: [number, number] | PositionCoords; // [lng, lat] or { lat, lon }
  capacity_mw: number;
  reserved_acres?: number;
  footprint_geojson?: Record<string, unknown> | null;
  boundary?: Record<string, unknown> | null;
}

export interface SiteDecision {
  confirmed: boolean;
  position?: [number, number] | PositionCoords;
  capacity_mw?: number;
  footprint_acres?: number;
  flexible_connection?: boolean;
}

export type RunStatusType =
  | 'running'
  | 'awaiting_confirmation'
  | 'completed'
  | 'rejected'
  | 'out_of_area'
  | 'not_viable'
  | 'failed'
  | 'pending';

export interface RunStatus {
  run_id: string;
  status: RunStatusType;
  stages?: string[];
  stage?: string;
  message?: string;
  capacity?: CapacityOutput;
  position?: [number, number] | PositionCoords;
  boundary?: Record<string, unknown> | null;
}

export interface FinancialCase {
  duration_hours?: 2 | 4 | 8;
  duration_h?: 2 | 4 | 8;
  capex_gbp: number;
  npv_gbp: number;
  irr_pct?: number;
  irr?: number;
}

export interface SentimentOutput {
  opposition_index?: number | null; // 0-1, None = unknown
  top_concerns?: string[];
  sources?: number;
  paragraphs?: number;
  artifacts?: Artifact[];
}

export interface ReportOutput {
  verdict: 'go' | 'maybe' | 'no_go';
  findings: Array<{ text: string; artifact_ids: string[] }>;
  report_path?: string;
  artifacts?: Artifact[];
}

export interface AssessmentResult {
  run_id: string;
  status?: RunStatusType;
  message?: string;
  site?: ConfirmedSite;
  capacity?: CapacityOutput;
  grid_connection?: {
    serving_substation: string;
    distance_km: number;
    voltage_kv: number;
    rag_status?: string;
    gsp_status?: string;
    tia_threshold_mw?: number;
  };
  land_planning?: {
    reserved_acres: number;
    green_belt: boolean;
    consenting_route: string;
    planning_risk: string;
  };
  sentiment?: SentimentOutput;
  durations?: {
    cases: FinancialCase[];
  };
  financials?: {
    cases: FinancialCase[];
    recommended_duration_hours?: number;
  };
  report?: ReportOutput;
  artifacts: Artifact[];
  run_dir?: string;
}

export interface TraceEvent {
  id: number;
  t: string;
  stage: string;
  msg: string;
}
