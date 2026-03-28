"use client";

import type { RouteStop } from "@/lib/api";
import { useRoutesStore } from "@/store/routes";

const HERITAGE_TYPE_COLORS: Record<string, string> = {
  patrimonio_inmueble: "bg-green-100 text-green-700",
  patrimonio_mueble: "bg-purple-100 text-purple-700",
  patrimonio_inmaterial: "bg-teal-100 text-teal-700",
  paisaje_cultural: "bg-sky-100 text-sky-700",
};

const HERITAGE_TYPE_LABELS: Record<string, string> = {
  patrimonio_inmueble: "Inmueble",
  patrimonio_mueble: "Mueble",
  patrimonio_inmaterial: "Inmaterial",
  paisaje_cultural: "Paisaje Cultural",
};

function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  if (hours > 0 && mins > 0) return `${hours}h ${mins}min`;
  if (hours > 0) return `${hours}h`;
  return `${mins}min`;
}

interface RouteStopCardProps {
  stop: RouteStop;
  showNarrative?: boolean;
}

export function RouteStopCard({ stop, showNarrative = true }: RouteStopCardProps) {
  const openStopDetail = useRoutesStore((s) => s.openStopDetail);

  const typeColor =
    HERITAGE_TYPE_COLORS[stop.heritage_type] ?? "bg-stone-100 text-stone-700";
  const typeLabel =
    HERITAGE_TYPE_LABELS[stop.heritage_type] ?? stop.heritage_type;

  const handleClick = () => {
    if (stop.heritage_asset_id) {
      openStopDetail(stop.heritage_asset_id);
    }
  };

  const isClickable = !!stop.heritage_asset_id;

  return (
    <div
      className={`rounded-xl border border-stone-200/60 bg-white shadow-sm transition-all overflow-hidden ${
        isClickable
          ? "hover:shadow-md hover:border-green-200/60 cursor-pointer"
          : ""
      }`}
      onClick={handleClick}
      role={isClickable ? "button" : undefined}
      tabIndex={isClickable ? 0 : undefined}
      onKeyDown={
        isClickable
          ? (e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                handleClick();
              }
            }
          : undefined
      }
    >
      {/* Image — full width header when available */}
      {stop.image_url && (
        <div className="w-full h-36 bg-stone-100 overflow-hidden">
          <img
            src={stop.image_url}
            alt={stop.title}
            className="w-full h-full object-cover"
          />
        </div>
      )}

      <div className="p-4 flex gap-3">
        {/* Order badge */}
        <div className="shrink-0">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-br from-green-600 to-emerald-700 text-white font-semibold text-sm shadow-sm">
            {stop.order}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          {/* Title */}
          <h4
            className={`font-semibold text-stone-900 leading-snug line-clamp-2 ${
              isClickable ? "hover:text-green-700 transition-colors" : ""
            }`}
          >
            {stop.title}
          </h4>

          {/* Metadata row */}
          <div className="flex flex-wrap items-center gap-1.5 mt-1.5">
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-medium ${typeColor}`}
            >
              {typeLabel}
            </span>
            <span className="text-xs text-stone-400 truncate">
              {stop.municipality ? `${stop.municipality}, ` : ""}
              {stop.province}
            </span>
            <span className="inline-flex items-center gap-1 rounded-full bg-stone-100 px-2 py-0.5 text-xs text-stone-500 shrink-0">
              <svg
                className="w-3 h-3"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
                />
              </svg>
              {formatDuration(stop.visit_duration_minutes)}
            </span>
          </div>

          {/* Asset description */}
          {stop.description && (
            <p className="text-xs text-stone-500 mt-2 leading-relaxed line-clamp-2">
              {stop.description}
            </p>
          )}

          {/* Narrative segment */}
          {showNarrative && stop.narrative_segment && (
            <p className="text-sm text-stone-600 mt-3 leading-relaxed">
              {stop.narrative_segment}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
