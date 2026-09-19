import {
  AssessmentRequest,
  AssessmentResult,
  CapacityOutput,
  RunStatus,
  SiteDecision,
  TraceEvent,
} from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
  status: number;
  data: any;

  constructor(status: number, message: string, data?: any) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

export async function startRun(
  req: AssessmentRequest
): Promise<{ run_id: string }> {
  const res = await fetch(`${API_BASE}/runs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    if (res.status === 503) {
      throw new ApiError(
        503,
        errorData.detail ||
          'Temporal server is unavailable. Start it with: temporal server start-dev',
        errorData
      );
    }
    throw new ApiError(
      res.status,
      errorData.detail || 'Failed to start assessment run',
      errorData
    );
  }

  return res.json();
}

export async function getRunStatus(id: string): Promise<RunStatus> {
  const res = await fetch(`${API_BASE}/runs/${id}/status`);
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorData.detail || 'Failed to get status', errorData);
  }
  const status = await res.json();
  if (status?.capacity) status.capacity = normalizeCapacity(status.capacity);
  return status;
}

export async function sendDecision(
  id: string,
  decision: SiteDecision
): Promise<{ allowed_min?: number; allowed_max?: number } | null> {
  const res = await fetch(`${API_BASE}/runs/${id}/decision`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(decision),
  });

  if (res.status === 204) {
    return null;
  }

  if (res.status === 422) {
    const data = await res.json();
    return {
      allowed_min: data.allowed_min,
      allowed_max: data.allowed_max,
    };
  }

  const errorData = await res.json().catch(() => ({}));
  throw new ApiError(res.status, errorData.detail || 'Decision submission failed', errorData);
}

export async function getRunResult(id: string): Promise<AssessmentResult> {
  const res = await fetch(`${API_BASE}/runs/${id}/result`);
  if (res.status === 409) {
    const data = await res.json().catch(() => ({}));
    throw new ApiError(409, 'Run is not finished yet', data);
  }
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorData.detail || 'Failed to get result', errorData);
  }
  return res.json();
}

export async function checkCapacity(
  position: [number, number],
  flexible: boolean
): Promise<CapacityOutput> {
  const res = await fetch(`${API_BASE}/capacity/check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ position, flexible }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new ApiError(res.status, errorData.detail || 'Capacity check failed', errorData);
  }

  return normalizeCapacity(await res.json());
}

export async function getAreasGeoJson(): Promise<any> {
  const res = await fetch(`${API_BASE}/data/areas.geojson`);
  if (!res.ok) {
    return null;
  }
  return res.json();
}

export async function getInspirePolygons(
  bbox: [number, number, number, number]
): Promise<any> {
  const [minLng, minLat, maxLng, maxLat] = bbox;
  const res = await fetch(
    `${API_BASE}/inspire?bbox=${minLng},${minLat},${maxLng},${maxLat}`
  );
  if (!res.ok) {
    return null;
  }
  return res.json();
}

/**
 * Subscribes to Server-Sent Events for a run's progress trace
 */
export function subscribeEvents(
  runId: string,
  onEvent: (event: TraceEvent) => void,
  lastEventId?: number
): () => void {
  const url = new URL(`${API_BASE}/runs/${runId}/events`);
  if (lastEventId !== undefined) {
    url.searchParams.set('last_event_id', lastEventId.toString());
  }

  const eventSource = new EventSource(url.toString());

  eventSource.onmessage = (e) => {
    try {
      const data: TraceEvent = JSON.parse(e.data);
      onEvent(data);
    } catch (err) {
      console.error('Failed to parse SSE trace event:', err);
    }
  };

  eventSource.onerror = (err) => {
    console.warn('SSE connection closed or error:', err);
  };

  return () => {
    eventSource.close();
  };
}

// LocationData for a coordinate: title boundary, substations with headroom, nearby projects, overhead lines.
export async function getSiteData(lat: number, lon: number): Promise<any> {
  const res = await fetch(`${API_BASE}/site-data?lat=${lat}&lon=${lon}`);
  if (!res.ok) {
    return null;
  }
  return res.json();
}

// The backend names things slightly differently from the UI types: map them once here.
function normalizeCapacity(cap: any): any {
  if (!cap) return cap;
  return {
    ...cap,
    serving_substation: cap.serving_substation ?? cap.substation,
    voltage_kv: cap.voltage_kv ?? cap.connection_voltage_kv,
    alternates: (cap.alternates ?? []).map((a: any) => ({
      ...a,
      name: a.name ?? a.substation,
      effective_headroom_mw: a.effective_headroom_mw ?? a.size_mw,
      is_marginal: a.is_marginal ?? a.marginal,
    })),
  };
}
