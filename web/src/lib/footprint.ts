/**
 * Footprint sizing and geometry utilities for Battery Energy Storage Systems (BESS)
 * 
 * Rules:
 * - Reserved area: 0.05 to 0.075 acres per MWh (energy = capacity_mw * duration_hours)
 * - Default duration: 4 hours
 * - Mid-range area used for polygon geometry = 0.0625 acres/MWh
 * - 1 acre = 4046.8564224 m²
 */

export interface AcreageEstimate {
  energyMWh: number;
  minAcres: number;
  maxAcres: number;
  midAcres: number;
}

export function calculateAcres(
  capacityMw: number,
  durationHours: number = 4
): AcreageEstimate {
  const energyMWh = Math.max(0, capacityMw) * durationHours;
  const minAcres = Number((energyMWh * 0.05).toFixed(2));
  const maxAcres = Number((energyMWh * 0.075).toFixed(2));
  const midAcres = Number((energyMWh * 0.0625).toFixed(2));

  return {
    energyMWh,
    minAcres,
    maxAcres,
    midAcres,
  };
}

/**
 * Generates a GeoJSON polygon feature centred on [lng, lat]
 * representing a square footprint matching the mid-range acres.
 */
export function generateFootprintPolygon(
  center: [number, number], // [lng, lat]
  capacityMw: number,
  durationHours: number = 4
): GeoJSON.Feature<GeoJSON.Polygon> {
  const [lng, lat] = center;
  const { midAcres } = calculateAcres(capacityMw, durationHours);

  // 1 acre = 4046.8564224 square meters
  const areaSqMeters = Math.max(midAcres, 0.1) * 4046.8564224;
  const sideMeters = Math.sqrt(areaSqMeters);
  const halfSideMeters = sideMeters / 2;

  // Degrees approximation:
  // 1 degree latitude ~ 111,139 meters
  // 1 degree longitude ~ 111,139 * cos(latitude) meters
  const latRad = (lat * Math.PI) / 180;
  const metersPerDegreeLat = 111139;
  const metersPerDegreeLng = 111139 * Math.cos(latRad);

  const deltaLat = halfSideMeters / metersPerDegreeLat;
  const deltaLng = halfSideMeters / metersPerDegreeLng;

  const coordinates: [number, number][][] = [
    [
      [lng - deltaLng, lat - deltaLat],
      [lng + deltaLng, lat - deltaLat],
      [lng + deltaLng, lat + deltaLat],
      [lng - deltaLng, lat + deltaLat],
      [lng - deltaLng, lat - deltaLat], // closed ring
    ],
  ];

  return {
    type: 'Feature',
    properties: {
      capacity_mw: capacityMw,
      duration_hours: durationHours,
      acres: midAcres,
      side_meters: Math.round(sideMeters),
    },
    geometry: {
      type: 'Polygon',
      coordinates,
    },
  };
}

/**
 * Calculates Haversine distance in kilometers between two [lng, lat] coordinates
 */
export function distanceKm(
  coord1: [number, number],
  coord2: [number, number]
): number {
  const [lng1, lat1] = coord1;
  const [lng2, lat2] = coord2;

  const R = 6371; // Earth radius in km
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLng = ((lng2 - lng1) * Math.PI) / 180;

  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLng / 2) *
      Math.sin(dLng / 2);

  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return Number((R * c).toFixed(3));
}

/**
 * Clamps a target [lng, lat] so it remains within maxKm of center [lng, lat]
 */
export function clampPositionWithinDistance(
  center: [number, number],
  target: [number, number],
  maxKm: number = 2.0
): [number, number] {
  const d = distanceKm(center, target);
  if (d <= maxKm) {
    return target;
  }

  // Linear interpolation along direction vector
  const ratio = maxKm / d;
  const clampedLng = center[0] + (target[0] - center[0]) * ratio;
  const clampedLat = center[1] + (target[1] - center[1]) * ratio;

  return [clampedLng, clampedLat];
}

/**
 * Generates sample HM Land Registry INSPIRE parcel polygons around a coordinate
 */
export function generateMockInspireParcels(
  center: [number, number]
): GeoJSON.FeatureCollection<GeoJSON.Polygon> {
  const [lng, lat] = center;
  const offsets = [
    [-0.002, -0.001, 0.0018, 0.0012],
    [0.0005, -0.0015, 0.002, 0.001],
    [-0.0015, 0.0008, 0.0015, 0.0014],
    [0.0008, 0.0005, 0.0022, 0.0016],
  ];

  const features: GeoJSON.Feature<GeoJSON.Polygon>[] = offsets.map((off, idx) => {
    const minLng = lng + off[0];
    const minLat = lat + off[1];
    const width = off[2];
    const height = off[3];

    return {
      type: 'Feature',
      properties: {
        id: `INSPIRE_${1000 + idx}`,
        national_cadastral_reference: `TGL${90000 + idx * 123}`,
        area_acres: Number((width * height * 100000).toFixed(2)),
      },
      geometry: {
        type: 'Polygon',
        coordinates: [
          [
            [minLng, minLat],
            [minLng + width, minLat],
            [minLng + width, minLat + height],
            [minLng, minLat + height],
            [minLng, minLat],
          ],
        ],
      },
    };
  });

  return {
    type: 'FeatureCollection',
    features,
  };
}
