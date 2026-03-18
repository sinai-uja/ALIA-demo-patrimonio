"use client";

import { useEffect } from "react";
import { MapContainer, TileLayer, Marker, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

// Fix default marker icon (webpack breaks Leaflet's default icon paths)
delete (L.Icon.Default.prototype as unknown as Record<string, unknown>)._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
});

const PROVINCE_COORDS: Record<string, [number, number]> = {
  "Almería": [36.834, -2.4637],
  "Cádiz": [36.527, -6.2886],
  "Córdoba": [37.888, -4.7794],
  "Granada": [37.177, -3.5986],
  "Huelva": [37.261, -6.9447],
  "Jaén": [37.780, -3.7849],
  "Málaga": [36.721, -4.4214],
  "Sevilla": [37.389, -5.9845],
};

const ANDALUSIA_CENTER: [number, number] = [37.4, -4.5];

function RecenterMap({ lat, lng, zoom }: { lat: number; lng: number; zoom: number }) {
  const map = useMap();
  useEffect(() => {
    map.setView([lat, lng], zoom);
  }, [map, lat, lng, zoom]);
  return null;
}

export default function AssetLocationMap({
  latitude,
  longitude,
  province,
}: {
  latitude?: number | null;
  longitude?: number | null;
  province?: string | null;
}) {
  const hasExact = latitude != null && longitude != null;
  let center: [number, number];
  let zoom: number;

  if (hasExact) {
    center = [latitude, longitude];
    zoom = 15;
  } else if (province && PROVINCE_COORDS[province]) {
    center = PROVINCE_COORDS[province];
    zoom = 10;
  } else {
    center = ANDALUSIA_CENTER;
    zoom = 7;
  }

  return (
    <div className="w-full h-48 rounded-xl overflow-hidden border border-stone-200">
      <MapContainer
        center={center}
        zoom={zoom}
        scrollWheelZoom={false}
        doubleClickZoom={false}
        dragging={false}
        touchZoom={false}
        boxZoom={false}
        keyboard={false}
        className="w-full h-full"
        zoomControl={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.esri.com">Esri</a>'
          url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
        />
        {hasExact && <Marker position={[latitude, longitude]} />}
        <RecenterMap lat={center[0]} lng={center[1]} zoom={zoom} />
      </MapContainer>
    </div>
  );
}
