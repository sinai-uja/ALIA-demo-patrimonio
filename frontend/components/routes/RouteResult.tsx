"use client";

import Link from "next/link";
import type { VirtualRoute } from "@/lib/api";
import { RouteStopCard } from "./RouteStopCard";
import { FeedbackButtons } from "@/components/shared/FeedbackButtons";

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

interface RouteResultProps {
  route: VirtualRoute;
}

/** Fallback layout for old routes without introduction/conclusion */
function LegacyLayout({ route }: { route: VirtualRoute }) {
  const paragraphs = route.narrative
    .split(/\n\n+/)
    .filter((p) => p.trim().length > 0);

  return (
    <>
      {/* Narrative */}
      <div className="space-y-3">
        {paragraphs.map((p, i) => (
          <p key={i} className="text-stone-600 leading-relaxed text-sm">
            {p}
          </p>
        ))}
      </div>

      {/* Stops timeline */}
      <div className="space-y-0">
        <h3 className="text-lg font-semibold text-stone-800 mb-4">Paradas</h3>
        <div className="relative">
          {route.stops.map((stop, i) => {
            const typeColor =
              HERITAGE_TYPE_COLORS[stop.heritage_type] ??
              "bg-stone-100 text-stone-700";
            const typeLabel =
              HERITAGE_TYPE_LABELS[stop.heritage_type] ?? stop.heritage_type;
            const description =
              stop.description.length > 500
                ? stop.description.slice(0, 500) + "..."
                : stop.description;

            return (
              <div key={stop.order} className="flex gap-4">
                {/* Timeline column */}
                <div className="flex flex-col items-center">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-green-600 to-emerald-700 text-white font-semibold text-sm shadow-sm">
                    {stop.order}
                  </div>
                  {i < route.stops.length - 1 && (
                    <div className="w-px flex-1 bg-stone-200 min-h-4" />
                  )}
                </div>

                {/* Content */}
                <div className="flex-1 min-w-0 pb-6">
                  <div className="flex items-start gap-2">
                    {stop.url ? (
                      <a
                        href={stop.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-semibold text-stone-900 hover:text-green-700 transition-colors"
                      >
                        {stop.title}
                      </a>
                    ) : (
                      <span className="font-semibold text-stone-900">
                        {stop.title}
                      </span>
                    )}
                  </div>
                  <div className="flex flex-wrap items-center gap-2 mt-1.5">
                    <span
                      className={`rounded-full px-2 py-0.5 text-xs font-medium ${typeColor}`}
                    >
                      {typeLabel}
                    </span>
                    <span className="text-xs text-stone-400">
                      {stop.municipality ? `${stop.municipality}, ` : ""}
                      {stop.province}
                    </span>
                    <span className="inline-flex items-center gap-1 rounded-full bg-stone-100 px-2 py-0.5 text-xs text-stone-500">
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
                  <p className="text-sm text-stone-600 mt-2 leading-relaxed">
                    {description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}

/** New layout with introduction, interleaved stop cards, and conclusion */
function InterleavedLayout({ route }: { route: VirtualRoute }) {
  return (
    <>
      {/* Introduction */}
      {route.introduction && (
        <p className="text-stone-600 leading-relaxed text-sm">
          {route.introduction}
        </p>
      )}

      {/* Stop cards with narrative outside */}
      <div className="space-y-5">
        {route.stops.map((stop) => (
          <div key={stop.order} className="space-y-3">
            {stop.narrative_segment && (
              <p className="text-sm text-stone-600 leading-relaxed px-1">
                {stop.narrative_segment}
              </p>
            )}
            <RouteStopCard stop={stop} />
          </div>
        ))}
      </div>

      {/* Conclusion */}
      {route.conclusion && (
        <p className="text-stone-600 leading-relaxed text-sm italic">
          {route.conclusion}
        </p>
      )}
    </>
  );
}

export function RouteResult({ route }: RouteResultProps) {
  const hasNewFormat = !!route.introduction;

  return (
    <div className="rounded-2xl border border-stone-200/60 bg-white p-6 sm:p-8 shadow-sm space-y-6">
      {/* Header */}
      <div className="space-y-2">
        <h2 className="text-2xl font-bold text-stone-900">{route.title}</h2>
        <div className="flex flex-wrap items-center gap-3 text-sm text-stone-500">
          <span className="inline-flex items-center gap-1">
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z"
              />
            </svg>
            {route.province}
          </span>
          <span>{route.stops.length} paradas</span>
          <span className="inline-flex items-center gap-1">
            <svg
              className="w-4 h-4"
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
            {formatDuration(route.total_duration_minutes)}
          </span>
          <FeedbackButtons targetType="route" targetId={route.id} />
        </div>
      </div>

      {/* Content: new or legacy layout */}
      {hasNewFormat ? (
        <InterleavedLayout route={route} />
      ) : (
        <LegacyLayout route={route} />
      )}

      {/* Link to detail */}
      <div className="pt-2 border-t border-stone-100">
        <Link
          href={`/routes/${route.id}`}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-green-700 hover:text-green-800 transition-colors"
        >
          Ver detalle
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="m4.5 19.5 15-15m0 0H8.25m11.25 0v11.25"
            />
          </svg>
        </Link>
      </div>
    </div>
  );
}
