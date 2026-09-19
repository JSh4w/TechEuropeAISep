'use client';

import React, { useEffect, useRef, useState, useCallback } from 'react';
import { Map, Marker, NavigationControl, Popup, StyleSpecification, GeoJSONSource } from 'maplibre-gl';
import { SubstationOption } from '../lib/types';
import { generateFootprintPolygon, distanceKm, clampPositionWithinDistance } from '../lib/footprint';
import { MapPin, Zap, AlertTriangle, Layers } from 'lucide-react';

interface SiteMapProps {
  initialCenter?: [number, number]; // [lng, lat]
  currentPosition: [number, number]; // [lng, lat]
  onPositionChange: (pos: [number, number]) => void;
  capacityMw: number;
  substations?: SubstationOption[];
  areasGeoJson?: GeoJSON.GeoJSON | null;
  inspireGeoJson?: GeoJSON.GeoJSON | null;
  siteData?: any; // LocationData from /site-data
  siteDataLoading?: boolean;
  maxDistanceKm?: number;
}

// Fallback raster OSM style that requires no API keys and works reliably anywhere
const DEFAULT_MAP_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    osm: {
      type: 'raster',
      tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
      tileSize: 256,
      attribution: '&copy; OpenStreetMap contributors',
    },
  },
  layers: [
    {
      id: 'osm-tiles',
      type: 'raster',
      source: 'osm',
      minzoom: 0,
      maxzoom: 19,
    },
  ],
};

export default function SiteMap({
  initialCenter = [0.1218, 51.5387], // Default London area
  currentPosition,
  onPositionChange,
  capacityMw,
  substations = [],
  areasGeoJson,
  inspireGeoJson,
  siteData,
  siteDataLoading = false,
  maxDistanceKm = 2.0,
}: SiteMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const pinMarkerRef = useRef<Marker | null>(null);
  const substationMarkersRef = useRef<Marker[]>([]);
  const siteDataMarkersRef = useRef<Marker[]>([]);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [distanceFromOrigin, setDistanceFromOrigin] = useState<number>(0);

  // Latest props for the marker's dragend handler, which is bound once
  const latestRef = useRef({ initialCenter, maxDistanceKm, onPositionChange });
  latestRef.current = { initialCenter, maxDistanceKm, onPositionChange };

  // Initialize Map
  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;

    const map = new Map({
      container: mapContainer.current,
      style: DEFAULT_MAP_STYLE,
      center: currentPosition,
      zoom: 14,
    });

    map.addControl(new NavigationControl({ showCompass: true }), 'top-right');

    map.on('load', () => {
      setMapLoaded(true);
    });

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update center when initialCenter changes
  useEffect(() => {
    if (mapRef.current && mapLoaded) {
      mapRef.current.easeTo({ center: currentPosition, zoom: 14 });
    }
  }, [initialCenter]);

  // Setup draggable site marker and footprint polygon layer
  useEffect(() => {
    if (!mapRef.current || !mapLoaded) return;
    const map = mapRef.current;

    // Draggable site marker
    if (!pinMarkerRef.current) {
      const el = document.createElement('div');
      el.className = 'site-marker flex items-center justify-center cursor-grab active:cursor-grabbing';
      el.innerHTML = `
        <div class="relative flex items-center justify-center">
          <div class="absolute w-8 h-8 bg-emerald-500/30 rounded-full animate-ping"></div>
          <div class="relative bg-emerald-600 text-white p-2 rounded-full shadow-lg border-2 border-white">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0Z"/><circle cx="12" cy="10" r="3"/></svg>
          </div>
        </div>
      `;

      const marker = new Marker({
        element: el,
        draggable: true,
      })
        .setLngLat(currentPosition)
        .addTo(map);

      marker.on('dragend', () => {
        const lngLat = marker.getLngLat();
        const rawPos: [number, number] = [lngLat.lng, lngLat.lat];
        const latest = latestRef.current;
        const clamped = clampPositionWithinDistance(latest.initialCenter, rawPos, latest.maxDistanceKm);

        marker.setLngLat(clamped);
        const dist = distanceKm(latest.initialCenter, clamped);
        setDistanceFromOrigin(dist);
        latest.onPositionChange(clamped);
      });

      pinMarkerRef.current = marker;
    } else {
      pinMarkerRef.current.setLngLat(currentPosition);
    }

    const dist = distanceKm(initialCenter, currentPosition);
    setDistanceFromOrigin(dist);
  }, [mapLoaded, currentPosition, initialCenter, maxDistanceKm]);

  // Update Footprint Polygon GeoJSON source
  useEffect(() => {
    if (!mapRef.current || !mapLoaded) return;
    const map = mapRef.current;

    const footprintGeoJson = generateFootprintPolygon(currentPosition, capacityMw, 4);

    const sourceId = 'site-footprint-source';
    const fillLayerId = 'site-footprint-fill';
    const lineLayerId = 'site-footprint-outline';

    const source = map.getSource(sourceId) as GeoJSONSource;

    if (source) {
      source.setData(footprintGeoJson);
    } else {
      map.addSource(sourceId, {
        type: 'geojson',
        data: footprintGeoJson,
      });

      map.addLayer({
        id: fillLayerId,
        type: 'fill',
        source: sourceId,
        paint: {
          'fill-color': '#10b981',
          'fill-opacity': 0.35,
        },
      });

      map.addLayer({
        id: lineLayerId,
        type: 'line',
        source: sourceId,
        paint: {
          'line-color': '#059669',
          'line-width': 2.5,
          'line-dasharray': [2, 1],
        },
      });
    }
  }, [mapLoaded, currentPosition, capacityMw]);

  // Add 2 km constraint radius circle layer
  useEffect(() => {
    if (!mapRef.current || !mapLoaded) return;
    const map = mapRef.current;

    // Approximate 2km radius circle as 64-vertex polygon
    const points = 64;
    const coords: [number, number][] = [];
    const [centerLng, centerLat] = initialCenter;
    const radiusMeters = maxDistanceKm * 1000;

    for (let i = 0; i <= points; i++) {
      const angle = (i * 2 * Math.PI) / points;
      const dLat = (radiusMeters * Math.cos(angle)) / 111139;
      const dLng = (radiusMeters * Math.sin(angle)) / (111139 * Math.cos((centerLat * Math.PI) / 180));
      coords.push([centerLng + dLng, centerLat + dLat]);
    }

    const circleGeoJson: GeoJSON.Feature<GeoJSON.Polygon> = {
      type: 'Feature',
      properties: { label: `${maxDistanceKm} km Pin Radius` },
      geometry: {
        type: 'Polygon',
        coordinates: [coords],
      },
    };

    const sourceId = 'pin-radius-source';
    const source = map.getSource(sourceId) as GeoJSONSource;

    if (source) {
      source.setData(circleGeoJson);
    } else {
      map.addSource(sourceId, {
        type: 'geojson',
        data: circleGeoJson,
      });

      map.addLayer({
        id: 'pin-radius-line',
        type: 'line',
        source: sourceId,
        paint: {
          'line-color': '#3b82f6',
          'line-width': 1.5,
          'line-dasharray': [4, 4],
          'line-opacity': 0.6,
        },
      });
    }
  }, [mapLoaded, initialCenter, maxDistanceKm]);

  // Render Substation Markers with Headroom and Marginal flag
  useEffect(() => {
    if (!mapRef.current || !mapLoaded) return;
    const map = mapRef.current;

    // Clear old substation markers
    substationMarkersRef.current.forEach((m) => m.remove());
    substationMarkersRef.current = [];

    if (siteData) return; // real substations (true coordinates) are drawn from LocationData below

    // For demonstration, if no coordinates in SubstationOption, place around center
    substations.forEach((sub, idx) => {
      // Mock offset if substation does not carry explicit coordinates
      const angle = (idx * 2 * Math.PI) / Math.max(substations.length, 1);
      const distOffset = (sub.distance_km || 0.8) * 1000;
      const latOffset = (distOffset * Math.cos(angle)) / 111139;
      const lngOffset =
        (distOffset * Math.sin(angle)) /
        (111139 * Math.cos((initialCenter[1] * Math.PI) / 180));
      const subCoords: [number, number] = [
        initialCenter[0] + lngOffset,
        initialCenter[1] + latOffset,
      ];

      const el = document.createElement('div');
      el.className = 'substation-marker';
      el.innerHTML = `
        <div class="group relative flex flex-col items-center">
          <div class="flex items-center gap-1 px-2 py-1 rounded-md shadow-md text-xs font-semibold ${
            sub.is_marginal
              ? 'bg-amber-100 text-amber-900 border border-amber-300'
              : 'bg-blue-600 text-white'
          }">
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            <span>${sub.name}</span>
            <span class="ml-1 opacity-90">(${sub.effective_headroom_mw} MW)</span>
            ${sub.is_marginal ? '<span class="bg-amber-300 text-amber-900 text-[10px] px-1 rounded">Marginal</span>' : ''}
          </div>
          <div class="w-2 h-2 bg-blue-600 rotate-45 -mt-1 ${sub.is_marginal ? 'bg-amber-300' : ''}"></div>
        </div>
      `;

      const popup = new Popup({ offset: 15 }).setHTML(`
        <div class="p-2 text-xs">
          <div class="font-bold text-sm text-zinc-900">${sub.name}</div>
          <div class="text-zinc-600">Distance: ${sub.distance_km.toFixed(2)} km</div>
          <div class="text-zinc-600">Voltage: ${sub.voltage_kv} kV</div>
          <div class="text-emerald-700 font-semibold mt-1">Headroom: ${sub.effective_headroom_mw} MW (Import: ${sub.import_headroom_mw} MW, Export: ${sub.export_headroom_mw} MW)</div>
          ${sub.is_marginal ? '<div class="text-amber-700 font-medium mt-1">⚠️ Marginal: over 1 km connection run</div>' : ''}
        </div>
      `);

      const marker = new Marker({ element: el })
        .setLngLat(subCoords)
        .setPopup(popup)
        .addTo(map);

      substationMarkersRef.current.push(marker);
    });
  }, [mapLoaded, substations, initialCenter, siteData]);

  // Real data layer from LocationData: title boundary, overhead lines, substations, generation / storage projects
  useEffect(() => {
    if (!mapRef.current || !mapLoaded) return;
    const map = mapRef.current;

    siteDataMarkersRef.current.forEach((m) => m.remove());
    siteDataMarkersRef.current = [];

    const grid = siteData?.deterministic?.grid;
    const esc = (v: unknown) => String(v ?? '').replace(/[<>&]/g, '');
    const fmt = (v: unknown, unit = '') => (typeof v === 'number' ? `${Math.round(v * 10) / 10}${unit}` : 'n/a');

    const shapes = {
      type: 'FeatureCollection',
      features: [
        ...((grid?.lines ?? []) as any[]).map((l) => ({
          type: 'Feature',
          properties: { layer: 'line', crosses: !!l.crosses_site },
          geometry: l.geometry,
        })),
      ],
    };
    const titleShape = {
      type: 'FeatureCollection',
      features: siteData?.title ? [{ type: 'Feature', properties: {}, geometry: siteData.title.geometry }] : [],
    };
    const titleSource = map.getSource('site-title-source') as GeoJSONSource;
    if (titleSource) {
      titleSource.setData(titleShape as any);
    } else {
      map.addSource('site-title-source', { type: 'geojson', data: titleShape as any });
      map.addLayer({
        id: 'site-title-fill',
        type: 'fill',
        source: 'site-title-source',
        paint: { 'fill-color': '#f97316', 'fill-opacity': 0.3 },
      });
      map.addLayer({
        id: 'site-title-halo',
        type: 'line',
        source: 'site-title-source',
        paint: { 'line-color': '#ffffff', 'line-width': 6 },
      });
      map.addLayer({
        id: 'site-title-outline',
        type: 'line',
        source: 'site-title-source',
        paint: { 'line-color': '#c2410c', 'line-width': 3 },
      });
    }
    // keep the title above the footprint and every other shape
    ['site-title-fill', 'site-title-halo', 'site-title-outline'].forEach((id) => map.getLayer(id) && map.moveLayer(id));

    const source = map.getSource('site-data-source') as GeoJSONSource;
    if (source) {
      source.setData(shapes as any);
    } else {
      map.addSource('site-data-source', { type: 'geojson', data: shapes as any });
      map.addLayer({
        id: 'site-data-lines',
        type: 'line',
        source: 'site-data-source',
        filter: ['==', ['get', 'layer'], 'line'],
        paint: {
          'line-color': ['case', ['get', 'crosses'], '#dc2626', '#7c3aed'],
          'line-width': 1.5,
          'line-dasharray': [3, 2],
        },
      });
    }
    if (!grid) return;

    const add = (lngLat: [number, number], html: string, popupHtml: string) => {
      const el = document.createElement('div');
      el.innerHTML = html;
      const marker = new Marker({ element: el })
        .setLngLat(lngLat)
        .setPopup(new Popup({ offset: 12 }).setHTML(`<div class="p-2 text-xs text-zinc-800">${popupHtml}</div>`))
        .addTo(map);
      siteDataMarkersRef.current.push(marker);
    };

    (grid.projects as any[]).slice(0, 40).forEach((p) => {
      const icon = p.is_storage ? '🔋' : p.is_solar ? '☀️' : '⚙️';
      add(
        [p.coords.lon, p.coords.lat],
        `<div class="text-sm leading-none bg-white/90 rounded-full border border-zinc-300 shadow p-1 cursor-pointer" title="${esc(p.name)}">${icon}</div>`,
        `<div class="font-bold">${esc(p.name) || 'Unnamed project'}</div>
         <div>${esc(p.technology)} · ${fmt(p.capacity_mw, ' MW')}${p.storage_mwh ? ` / ${fmt(p.storage_mwh, ' MWh')}` : ''}</div>
         <div>${esc(p.status)} · ${esc(p.operator)} · ${fmt(p.distance_km, ' km')}</div>`
      );
    });

    (grid.substations as any[]).slice(0, 12).forEach((sub) => {
      const h = sub.headroom;
      const twoWay = h ? Math.max(0, Math.min(h.generation_mw ?? 0, h.demand ?? 0)) : null;
      const tone =
        twoWay === null
          ? 'bg-zinc-600 text-white'
          : twoWay >= 5
            ? 'bg-emerald-600 text-white'
            : twoWay > 0
              ? 'bg-amber-500 text-white'
              : 'bg-red-600 text-white';
      add(
        [sub.coords.lon, sub.coords.lat],
        `<div class="flex items-center gap-1 px-2 py-1 rounded-md shadow-md text-[11px] font-semibold cursor-pointer ${tone}">
           <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
           <span>${esc(sub.name)}</span>
           <span class="opacity-90">${twoWay === null ? '' : `(${fmt(twoWay, ' MW')})`}</span>
         </div>`,
        `<div class="font-bold text-sm">${esc(sub.name)}</div>
         <div>${esc(sub.operator)} · ${esc(sub.kind)} · ${esc(sub.voltages ?? sub.voltage_kv)} kV · ${fmt(sub.distance_km, ' km')}</div>
         ${
           h
             ? `<div class="font-semibold mt-1">Import ${fmt(h.demand)} ${esc(h.demand_unit)} · Export ${fmt(h.generation_mw, ' MW')}</div>
                <div>${esc(h.generation_constraint ?? h.demand_constraint ?? '')}</div>`
             : '<div class="mt-1">No published headroom</div>'
         }
         ${sub.gsp ? `<div>GSP: ${esc(sub.gsp)}${sub.bsp ? ` · BSP: ${esc(sub.bsp)}` : ''}</div>` : ''}`
      );
    });
  }, [mapLoaded, siteData]);

  // Render Distribution Areas GeoJSON outline if provided
  useEffect(() => {
    if (!mapRef.current || !mapLoaded || !areasGeoJson) return;
    const map = mapRef.current;
    const sourceId = 'distribution-areas-source';

    const source = map.getSource(sourceId) as GeoJSONSource;
    if (source) {
      source.setData(areasGeoJson);
    } else {
      map.addSource(sourceId, {
        type: 'geojson',
        data: areasGeoJson,
      });

      map.addLayer({
        id: 'distribution-areas-fill',
        type: 'fill',
        source: sourceId,
        paint: {
          'fill-color': '#6366f1',
          'fill-opacity': 0.05,
        },
      });

      map.addLayer({
        id: 'distribution-areas-line',
        type: 'line',
        source: sourceId,
        paint: {
          'line-color': '#4f46e5',
          'line-width': 2,
          'line-dasharray': [3, 2],
          'line-opacity': 0.7,
        },
      });
    }
  }, [mapLoaded, areasGeoJson]);

  // Render INSPIRE polygons overlay if provided
  useEffect(() => {
    if (!mapRef.current || !mapLoaded || !inspireGeoJson) return;
    const map = mapRef.current;
    const sourceId = 'inspire-parcels-source';

    const source = map.getSource(sourceId) as GeoJSONSource;
    if (source) {
      source.setData(inspireGeoJson);
    } else {
      map.addSource(sourceId, {
        type: 'geojson',
        data: inspireGeoJson,
      });

      map.addLayer({
        id: 'inspire-parcels-line',
        type: 'line',
        source: sourceId,
        paint: {
          'line-color': '#e11d48',
          'line-width': 1.5,
          'line-opacity': 0.7,
        },
      });

      map.addLayer({
        id: 'inspire-parcels-fill',
        type: 'fill',
        source: sourceId,
        paint: {
          'fill-color': '#f43f5e',
          'fill-opacity': 0.1,
        },
      });
    }
  }, [mapLoaded, inspireGeoJson]);

  return (
    <div className="relative w-full h-[72vh] min-h-[560px] rounded-xl overflow-hidden border border-zinc-200 dark:border-zinc-800 shadow-sm">
      <div ref={mapContainer} className="w-full h-[72vh] min-h-[560px]" />

      {/* Map Overlay Badges */}
      <div className="absolute top-3 left-3 flex flex-col gap-2 pointer-events-none z-10">
        <div className="bg-white/95 dark:bg-zinc-900/95 backdrop-blur px-3 py-1.5 rounded-lg shadow-sm border border-zinc-200 dark:border-zinc-700 text-xs font-medium flex items-center gap-2">
          <MapPin className="w-4 h-4 text-emerald-600" />
          <span>
            Pin: {currentPosition[1].toFixed(5)}, {currentPosition[0].toFixed(5)}
          </span>
          <span className="text-zinc-500">
            ({distanceFromOrigin.toFixed(2)} km from origin)
          </span>
        </div>

        {substations.length > 0 && (
          <div className="bg-white/95 dark:bg-zinc-900/95 backdrop-blur px-3 py-1.5 rounded-lg shadow-sm border border-zinc-200 dark:border-zinc-700 text-xs text-zinc-600 dark:text-zinc-300 flex items-center gap-2">
            <Zap className="w-3.5 h-3.5 text-blue-600" />
            <span>{substations.length} Substations mapped</span>
          </div>
        )}
      </div>

      <div className="absolute bottom-3 left-3 bg-white/95 dark:bg-zinc-900/95 backdrop-blur px-3 py-1.5 rounded-lg shadow-sm border border-zinc-200 dark:border-zinc-700 text-xs text-zinc-500 pointer-events-none z-10 flex items-center gap-2">
        <span className="inline-block w-2.5 h-2.5 rounded-sm bg-emerald-500 opacity-60"></span>
        <span>Generated Footprint (drag pin to position)</span>
        {siteData && (
          <>
            <span className="inline-block w-2.5 h-2.5 rounded-sm border-2 border-orange-700 bg-orange-300 ml-2"></span>
            <span>
              Title {siteData.title ? `${siteData.title.area_ha.toFixed(2)} ha` : 'not registered'}
            </span>
            {siteData.title && (
              <button
                type="button"
                className="pointer-events-auto underline text-orange-700 font-semibold"
                onClick={() => {
                  const [minLon, minLat, maxLon, maxLat] = siteData.title.bbox;
                  mapRef.current?.fitBounds(
                    [
                      [minLon, minLat],
                      [maxLon, maxLat],
                    ],
                    { padding: 120, maxZoom: 18 }
                  );
                }}
              >
                zoom to title
              </button>
            )}
            <span className="ml-2">⚡ substations · 🔋 storage · ☀️ solar · ⚙️ other · ┄ overhead lines</span>
          </>
        )}
        {siteDataLoading && <span className="ml-2 text-emerald-600 animate-pulse">Loading live site data…</span>}
      </div>
    </div>
  );
}

