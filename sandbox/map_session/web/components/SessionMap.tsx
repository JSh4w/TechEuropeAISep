"use client";
// Leaflet touches `window`, so this is loaded with `dynamic(..., { ssr: false })` from the session page.

import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { MapContainer, Marker, Polygon as LeafletPolygon, TileLayer } from "react-leaflet";
import type { Polygon } from "@/lib/types";

type LatLng = [number, number];

// GeoJSON is [lng, lat] with a closing point; Leaflet wants [lat, lng] without it.
const toLatLngs = (p: Polygon): LatLng[] => p.coordinates[0].slice(0, -1).map(([lng, lat]) => [lat, lng]);
const toPolygon = (pts: LatLng[]): Polygon => {
  const ring = pts.map(([lat, lng]) => [lng, lat]);
  return { type: "Polygon", coordinates: [[...ring, ring[0]]] };
};

const handle = L.divIcon({ className: "vertex-handle", iconSize: [14, 14] });

type Props = {
  center: LatLng;
  titleBoundary: Polygon | null;
  suggested: Polygon | null;
  area: Polygon | null;
  ok: boolean;
  editable: boolean;
  onChange: (area: Polygon) => void; // called on drag end
  onDraft: (area: Polygon) => void; // called while dragging, for a live outline
};

export default function SessionMap({ center, titleBoundary, suggested, area, ok, editable, onChange, onDraft }: Props) {
  const pts = area ? toLatLngs(area) : [];

  const moved = (i: number, e: L.LeafletEvent, done: boolean) => {
    const { lat, lng } = (e.target as L.Marker).getLatLng();
    const next = pts.map((p, j): LatLng => (j === i ? [lat, lng] : p));
    (done ? onChange : onDraft)(toPolygon(next));
  };

  return (
    <MapContainer center={center} zoom={18} maxZoom={21} className="map">
      <TileLayer
        url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        attribution="Imagery &copy; Esri"
        maxNativeZoom={19}
        maxZoom={21}
      />
      {titleBoundary && (
        <LeafletPolygon
          positions={toLatLngs(titleBoundary)}
          pathOptions={{ color: "#f5f5f5", weight: 2, dashArray: "6 6", fill: false }}
        />
      )}
      {suggested && (
        <LeafletPolygon
          positions={toLatLngs(suggested)}
          pathOptions={{ color: "#a78bfa", weight: 1, dashArray: "2 4", fillOpacity: 0.05 }}
        />
      )}
      {area && (
        <LeafletPolygon
          positions={pts}
          pathOptions={{ color: ok ? "#22c55e" : "#ef4444", weight: 3, fillOpacity: 0.25 }}
        />
      )}
      {editable &&
        pts.map((p, i) => (
          <Marker
            key={i}
            position={p}
            icon={handle}
            draggable
            eventHandlers={{ drag: (e) => moved(i, e, false), dragend: (e) => moved(i, e, true) }}
          />
        ))}
    </MapContainer>
  );
}
