"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { traces } from "@/lib/api";
import type { RouteHistoryResponse, TraceSummary } from "@/lib/api";

interface RouteHistoryTimelineProps {
  routeId: string;
}

interface DotStyle {
  dotClassName: string;
  iconClassName: string;
}

function dotStyleFor(pipelineMode: string | null | undefined): DotStyle {
  switch (pipelineMode) {
    case "route_add_stop":
      return {
        dotClassName: "bg-green-500 border-green-200",
        iconClassName: "text-green-700",
      };
    case "route_remove_stop":
      return {
        dotClassName: "bg-red-500 border-red-200",
        iconClassName: "text-red-700",
      };
    case "route_generation":
    case "route_generation_stream":
    default:
      return {
        dotClassName: "bg-amber-500 border-amber-200",
        iconClassName: "text-amber-700",
      };
  }
}

function actionLabelFor(pipelineMode: string | null | undefined): string {
  switch (pipelineMode) {
    case "route_generation":
      return "Generación de ruta";
    case "route_generation_stream":
      return "Generación de ruta (streaming)";
    case "route_add_stop":
      return "Adición de parada";
    case "route_remove_stop":
      return "Eliminación de parada";
    default:
      return "Evento de ruta";
  }
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("es-ES", {
    day: "2-digit",
    month: "2-digit",
    year: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function TimelineItem({
  trace,
  isLast,
}: {
  trace: TraceSummary;
  isLast: boolean;
}) {
  const { dotClassName } = dotStyleFor(trace.pipeline_mode);
  const action = actionLabelFor(trace.pipeline_mode);

  return (
    <div className="relative flex gap-3">
      <div className="flex flex-col items-center">
        <div
          className={`mt-1 h-3 w-3 shrink-0 rounded-full border-2 ${dotClassName}`}
        />
        {!isLast && <div className="mt-1 w-px flex-1 bg-stone-200" />}
      </div>
      <Link
        href={`/admin/traces?trace=${trace.id}`}
        className={`flex-1 ${isLast ? "pb-0" : "pb-5"} group`}
      >
        <div className="rounded-lg border border-stone-200/60 bg-white px-3 py-2.5 shadow-sm transition-all group-hover:border-green-400 group-hover:shadow-md">
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-sm font-medium text-stone-800">{action}</span>
            <span className="shrink-0 text-xs tabular-nums text-stone-400">
              {formatDate(trace.created_at)}
            </span>
          </div>
          <p className="mt-0.5 text-xs text-stone-500 truncate">
            {trace.query || "(sin descripción)"}
          </p>
          <p className="mt-1 text-[11px] text-stone-400">
            por <span className="font-medium text-stone-600">{trace.username}</span>
            {trace.user_profile_type ? ` · ${trace.user_profile_type}` : ""}
          </p>
        </div>
      </Link>
    </div>
  );
}

interface FetchState {
  history: RouteHistoryResponse | null;
  loading: boolean;
  error: string | null;
  routeId: string | null;
}

const INITIAL_FETCH_STATE: FetchState = {
  history: null,
  loading: true,
  error: null,
  routeId: null,
};

export default function RouteHistoryTimeline({ routeId }: RouteHistoryTimelineProps) {
  const [state, setState] = useState<FetchState>(INITIAL_FETCH_STATE);
  // Reset state when routeId changes (during render, setState is allowed for derived state).
  if (state.routeId !== routeId) {
    setState({ history: null, loading: true, error: null, routeId });
  }
  const { history, loading, error } = state;

  useEffect(() => {
    let cancelled = false;
    traces
      .listRouteHistory(routeId)
      .then((data) => {
        if (!cancelled) {
          setState({ history: data, loading: false, error: null, routeId });
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setState({
            history: null,
            loading: false,
            error: err instanceof Error ? err.message : "Error al cargar el historial",
            routeId,
          });
        }
      });
    return () => {
      cancelled = true;
    };
  }, [routeId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-10">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-stone-300 border-t-green-600" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 border border-red-100 px-4 py-3 text-xs text-red-700">
        {error}
      </div>
    );
  }

  if (!history || history.traces.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-10 text-center">
        <svg
          className="w-10 h-10 text-stone-200 mb-3"
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
        <p className="text-sm font-medium text-stone-500">Sin historial</p>
        <p className="text-xs text-stone-400 mt-1">
          Aún no hay eventos registrados para esta ruta
        </p>
      </div>
    );
  }

  const { aggregate, traces: items } = history;
  const summaryParts: string[] = [
    `${aggregate.total_events} evento${aggregate.total_events !== 1 ? "s" : ""}`,
    `${aggregate.generation_count} generación${aggregate.generation_count !== 1 ? "es" : ""}`,
    `${aggregate.additions_count} adición${aggregate.additions_count !== 1 ? "es" : ""}`,
    `${aggregate.removals_count} eliminación${aggregate.removals_count !== 1 ? "es" : ""}`,
  ];

  return (
    <div className="space-y-4">
      <div className="rounded-xl border border-stone-200/60 bg-stone-50 px-4 py-3">
        <p className="text-xs font-semibold uppercase tracking-wider text-stone-400">
          Resumen
        </p>
        <p className="mt-1 text-sm text-stone-700">{summaryParts.join(" · ")}</p>
      </div>

      <div className="space-y-0">
        {items.map((trace, i) => (
          <TimelineItem
            key={trace.id}
            trace={trace}
            isLast={i === items.length - 1}
          />
        ))}
      </div>
    </div>
  );
}
