'use client';

import React, { useEffect, useRef, useState } from 'react';
import { Map, Marker, NavigationControl, Popup, StyleSpecification, GeoJSONSource } from 'maplibre-gl';
import { SubstationOption } from '../lib/types';
import { generateFootprintPolygon, distanceKm, clampPositionWithinDistance } from '../lib/footprint';
import { MapPin, Zap, Layers, Navigation, Info } from 'lucide-react';

interface SiteMapProps {
  initialCenter?: [number, number]; // [lng, lat]
  currentPosition: [number, number]; // [lng, lat]
  onPositionChange: (pos: [number, number]) => void;
  capacityMw: number;
  substations?: SubstationOption[];
  areasGeoJson?: GeoJSON.GeoJSON | null;
  inspireGeoJson?: GeoJSON.GeoJSON | null;
  maxDistanceKm?: number;
}

// Clean, modern Esri World Street Map raster style (no API key required, reliable, no watermark)
const STREETS_MAP_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    esri_streets: {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
      attribution: '&copy; Esri &copy; OpenStreetMap contributors',
    },
  },
  layers: [
    {
      id: 'esri-street-tiles',
      type: 'raster',
      source: 'esri_streets',
      minzoom: 0,
      maxzoom: 19,
    },
  ],
};

const SATELLITE_MAP_STYLE: StyleSpecification = {
  version: 8,
  sources: {
    esri: {
      type: 'raster',
      tiles: [
        'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
      ],
      tileSize: 256,
      attribution: '&copy; Esri, Maxar, Earthstar Geographics',
    },
  },
  layers: [
    {
      id: 'esri-tiles',
      type: 'raster',
      source: 'esri',
      minzoom: 0,
      maxzoom: 19,
    },
  ],
};

export default function SiteMap({
  initialCenter = [-0.1132, 51.5014],
  currentPosition,
  onPositionChange,
  capacityMw,
  substations = [],
  areasGeoJson,
  inspireGeoJson,
  maxDistanceKm = 2.0,
}: SiteMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const mapRef = useRef<Map | null>(null);
  const pinMarkerRef = useRef<Marker | null>(null);
  const substationMarkersRef = useRef<Marker[]>([]);
  const [mapLoaded, setMapLoaded] = useState(false);
  const [distanceFromOrigin, setDistanceFromOrigin] = useState<number>(0);
  const [mapMode, setMapMode] = useState<'streets' | 'satellite'>('streets');

  // Initialize Map
  useEffect(() => {
    if (!mapContainer.current || mapRef.current) return;

    const map = new Map({
      container: mapContainer.current,
      style: STREETS_MAP_STYLE,
      center: currentPosition,
      zoom: 14.5,
      pitch: 15,
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

  // Handle map style switch (Streets vs Satellite)
  const handleToggleMapMode = () => {
    if (!mapRef.current) return;
    const nextMode = mapMode === 'streets' ? 'satellite' : 'streets';
    setMapMode(nextMode);
    mapRef.current.setStyle(nextMode === 'streets' ? STREETS_MAP_STYLE : SATELLITE_MAP_STYLE);
    // Reload state triggers layer re-addition
    setMapLoaded(false);
    mapRef.current.once('style.load', () => {
      setMapLoaded(true);
    });
  };

  // Update center when initialCenter changes
  useEffect(() => {
    if (mapRef.current && mapLoaded) {
      mapRef.current.easeTo({ center: currentPosition, zoom: 14.5 });
    }
  }, [initialCenter]);

  // Setup draggable site marker
  useEffect(() => {
    if (!mapRef.current || !mapLoaded) return;
    const map = mapRef.current;

    if (!pinMarkerRef.current) {
      const el = document.createElement('div');
      el.className = 'site-marker flex items-center justify-center cursor-grab active:cursor-grabbing group';
      el.innerHTML = `
        <div class="relative flex items-center justify-center">
          <div class="absolute -inset-3 bg-emerald-500/20 rounded-full animate-ping pointer-events-none"></div>
          <div class="relative bg-emerald-600 text-white p-2.5 rounded-full shadow-xl border-2 border-white ring-2 ring-emerald-500/40 transition-transform transform group-hover:scale-110">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M13 2 3 14h9l-1 8 10-12h-9l1-8z"/>
            </svg>
          </div>
          <div class="absolute -bottom-8 bg-zinc-950 text-white font-mono text-[10px] font-semibold px-2 py-0.5 rounded shadow-lg whitespace-nowrap border border-zinc-800 pointer-events-none">
            BESS Point
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
        const clamped = clampPositionWithinDistance(initialCenter, rawPos, maxDistanceKm);
        marker.setLngLat(clamped);
        const dist = distanceKm(initialCenter, clamped);
        setDistanceFromOrigin(dist);
        onPositionChange(clamped);
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
          'fill-opacity': 0.28,
        },
      });

      map.addLayer({
        id: lineLayerId,
        type: 'line',
        source: sourceId,
        paint: {
          'line-color': '#059669',
          'line-width': 2.5,
          'line-dasharray': [3, 1.5],
        },
      });
    }
  }, [mapLoaded, currentPosition, capacityMw]);

  // Add 2 km constraint radius circle layer
  useEffect(() => {
    if (!mapRef.current || !mapLoaded) return;
    const map = mapRef.current;

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
      properties: { label: `${maxDistanceKm} km Screening Radius` },
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
          'line-color': '#0284c7',
          'line-width': 1.5,
          'line-dasharray': [3, 3],
          'line-opacity': 0.6,
        },
      });
    }
  }, [mapLoaded, initialCenter, maxDistanceKm]);

  // Render Substation Markers & Cable Vector Ray
  useEffect(() => {
    if (!mapRef.current || !mapLoaded) return;
    const map = mapRef.current;

    // Clear old markers
    substationMarkersRef.current.forEach((m) => m.remove());
    substationMarkersRef.current = [];

    const calculatedSubstations: Array<{ coords: [number, number]; sub: SubstationOption }> = [];

    substations.forEach((sub, idx) => {
      const angle = (idx * 2 * Math.PI) / Math.max(substations.length, 1) + 0.35;
      const distOffset = (sub.distance_km || 0.8) * 1000;
      const latOffset = (distOffset * Math.cos(angle)) / 111139;
      const lngOffset =
        (distOffset * Math.sin(angle)) /
        (111139 * Math.cos((initialCenter[1] * Math.PI) / 180));
      const subCoords: [number, number] = [
        initialCenter[0] + lngOffset,
        initialCenter[1] + latOffset,
      ];

      calculatedSubstations.push({ coords: subCoords, sub });

      const el = document.createElement('div');
      el.className = 'substation-marker group cursor-pointer';
      el.innerHTML = `
        <div class="relative flex flex-col items-center">
          <div class="flex items-center gap-1.5 px-2.5 py-1 rounded-lg shadow-md text-xs font-semibold ${
            sub.is_marginal
              ? 'bg-amber-50 text-amber-900 border border-amber-300 dark:bg-amber-950 dark:text-amber-100'
              : 'bg-blue-600 text-white border border-blue-500 shadow-blue-500/20'
          }">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
            <span class="tracking-tight">${sub.name}</span>
            <span class="ml-0.5 opacity-90 font-mono text-[11px]">${sub.effective_headroom_mw}MW</span>
            ${sub.is_marginal ? '<span class="bg-amber-200 text-amber-950 text-[9px] px-1 rounded font-bold uppercase">Marginal</span>' : ''}
          </div>
          <div class="w-2 h-2 rotate-45 -mt-1 ${sub.is_marginal ? 'bg-amber-300' : 'bg-blue-600'}"></div>
        </div>
      `;

      const popup = new Popup({ offset: 15, closeButton: false }).setHTML(`
        <div class="p-2.5 text-xs font-sans space-y-1">
          <div class="font-bold text-sm text-foreground">${sub.name}</div>
          <div class="text-muted-foreground flex justify-between gap-3">
            <span>Route Distance:</span>
            <span class="font-mono font-medium text-foreground">${sub.distance_km.toFixed(2)} km</span>
          </div>
          <div class="text-muted-foreground flex justify-between gap-3">
            <span>Primary Voltage:</span>
            <span class="font-mono font-medium text-foreground">${sub.voltage_kv} kV</span>
          </div>
          <div class="text-emerald-600 dark:text-emerald-400 font-semibold pt-1 border-t border-border flex justify-between">
            <span>Available Headroom:</span>
            <span class="font-mono">${sub.effective_headroom_mw} MW</span>
          </div>
          ${sub.is_marginal ? '<div class="text-amber-600 font-medium text-[11px] pt-0.5">Note: Distance > 1km introduces higher contestable cabling capex.</div>' : ''}
        </div>
      `);

      const marker = new Marker({ element: el })
        .setLngLat(subCoords)
        .setPopup(popup)
        .addTo(map);

      substationMarkersRef.current.push(marker);
    });

    // Draw Cable Vector Ray to the primary serving substation
    if (calculatedSubstations.length > 0) {
      const primary = calculatedSubstations[0];
      const rayGeoJson: GeoJSON.Feature<GeoJSON.LineString> = {
        type: 'Feature',
        properties: {},
        geometry: {
          type: 'LineString',
          coordinates: [currentPosition, primary.coords],
        },
      };

      const sourceId = 'cable-ray-source';
      const source = map.getSource(sourceId) as GeoJSONSource;
      if (source) {
        source.setData(rayGeoJson);
      } else {
        map.addSource(sourceId, {
          type: 'geojson',
          data: rayGeoJson,
        });

        map.addLayer({
          id: 'cable-ray-line',
          type: 'line',
          source: sourceId,
          paint: {
            'line-color': '#0ea5e9',
            'line-width': 2.5,
            'line-dasharray': [4, 2],
            'line-opacity': 0.85,
          },
        });
      }
    }
  }, [mapLoaded, substations, initialCenter, currentPosition]);

  // Render INSPIRE Land Registry Parcels if present
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
          'fill-opacity': 0.08,
        },
      });
    }
  }, [mapLoaded, inspireGeoJson]);

  return (
    <div className="relative w-full h-[480px] rounded-2xl overflow-hidden border border-border shadow-md bg-muted">
      <div ref={mapContainer} className="w-full h-full" />

      {/* Top Left: Location & Pin Coordinate Telemetry */}
      <div className="absolute top-3.5 left-3.5 flex flex-col gap-2 pointer-events-none z-10">
        <div className="bg-card/90 backdrop-blur-md px-3.5 py-2 rounded-xl shadow-sm border border-border/80 text-xs font-medium flex items-center gap-2.5">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
          <span className="font-mono text-foreground font-semibold">
            {currentPosition[1].toFixed(5)}°N, {Math.abs(currentPosition[0]).toFixed(5)}°{currentPosition[0] >= 0 ? 'E' : 'W'}
          </span>
          <span className="text-muted-foreground text-[11px] font-mono border-l border-border pl-2">
            +{distanceFromOrigin.toFixed(2)} km offset
          </span>
        </div>

        {substations.length > 0 && (
          <div className="bg-card/90 backdrop-blur-md px-3.5 py-1.5 rounded-xl shadow-sm border border-border/80 text-xs text-foreground/90 flex items-center gap-2">
            <Zap className="w-3.5 h-3.5 text-blue-500" />
            <span>{substations.length} Substation Nodes Polled</span>
          </div>
        )}
      </div>

      {/* Top Right: Layer Switcher & Controls */}
      <div className="absolute top-3.5 right-14 z-10 flex items-center gap-2">
        <button
          type="button"
          onClick={handleToggleMapMode}
          className="bg-card/90 hover:bg-card text-foreground backdrop-blur-md px-3 py-1.5 rounded-lg shadow-sm border border-border text-xs font-semibold flex items-center gap-1.5 transition active:scale-95 cursor-pointer"
        >
          <Layers className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
          <span>{mapMode === 'streets' ? 'Satellite View' : 'Street Map'}</span>
        </button>
      </div>

      {/* Bottom Floating Legend Bar */}
      <div className="absolute bottom-3.5 left-3.5 right-3.5 flex flex-wrap items-center justify-between gap-2 pointer-events-none z-10">
        <div className="bg-card/90 backdrop-blur-md px-3 py-1.5 rounded-xl shadow-sm border border-border/80 text-[11px] text-muted-foreground flex items-center gap-3">
          <div className="flex items-center gap-1.5">
            <span className="inline-block w-2.5 h-2.5 rounded-sm bg-emerald-500 opacity-80"></span>
            <span className="font-medium text-foreground">BESS Footprint ({capacityMw} MW)</span>
          </div>
          <div className="flex items-center gap-1.5 border-l border-border pl-3">
            <span className="inline-block w-4 h-0.5 border-t border-dashed border-sky-500"></span>
            <span>Cable Connection Run</span>
          </div>
          {inspireGeoJson && (
            <div className="flex items-center gap-1.5 border-l border-border pl-3">
              <span className="inline-block w-2.5 h-2.5 rounded-sm bg-rose-500 opacity-70"></span>
              <span>Cadastral Boundary</span>
            </div>
          )}
        </div>

        <div className="hidden sm:flex bg-card/90 backdrop-blur-md px-2.5 py-1 rounded-lg shadow-sm border border-border/80 text-[10px] text-muted-foreground items-center gap-1">
          <Info className="w-3 h-3 text-emerald-600" />
          <span>Drag marker to adjust location within 2 km</span>
        </div>
      </div>
    </div>
  );
}
