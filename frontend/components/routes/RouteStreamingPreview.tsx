"use client";

import { useRoutesStore } from "@/store/routes";
import { RouteStopCard } from "./RouteStopCard";

const STEP_LABELS: Record<string, string> = {
  query_extraction: "Consulta",
  embedding: "Embedding",
  vector_search: "Busqueda",
  rag: "RAG",
  reranker: "Reranker",
  stop_selection: "Paradas",
  asset_lookup: "Assets",
  narrative: "Narrativa",
  narrative_generation: "Narrativa",
  saving: "Guardando",
};

function StepBadge({ step }: { step: { step: string; status: string; detail?: string } }) {
  const label = STEP_LABELS[step.step] ?? step.step;
  const isDone = step.status === "done";
  const isRunning = step.status === "running";

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-all duration-300 ${
        isDone
          ? "bg-green-100 text-green-700"
          : isRunning
            ? "bg-blue-100 text-blue-700"
            : "bg-stone-100 text-stone-500"
      }`}
      title={step.detail}
    >
      {isDone && (
        <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
        </svg>
      )}
      {isRunning && (
        <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
      )}
      {label}
    </span>
  );
}

function SkeletonStopCard({ order }: { order: number }) {
  return (
    <div className="rounded-xl border border-stone-200/60 bg-white shadow-sm overflow-hidden animate-pulse">
      <div className="flex">
        <div className="w-28 shrink-0 bg-stone-100 h-20" />
        <div className="p-3 flex gap-2.5 flex-1 min-w-0">
          <div className="shrink-0">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-stone-200 text-stone-400 font-semibold text-xs">
              {order}
            </div>
          </div>
          <div className="flex-1 space-y-2 py-1">
            <div className="h-3.5 bg-stone-200 rounded w-3/4" />
            <div className="h-2.5 bg-stone-100 rounded w-1/2" />
          </div>
        </div>
      </div>
    </div>
  );
}

function NarrativeSpinner() {
  return (
    <div className="flex items-center gap-2 px-1 py-1">
      <svg className="w-3.5 h-3.5 animate-spin text-green-500" fill="none" viewBox="0 0 24 24">
        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
      </svg>
      <span className="text-xs text-stone-400 italic">Generando narrativa...</span>
    </div>
  );
}

export function RouteStreamingPreview() {
  const steps = useRoutesStore((s) => s.streamingSteps);
  const stops = useRoutesStore((s) => s.streamingStops);
  const title = useRoutesStore((s) => s.streamingTitle);
  const introduction = useRoutesStore((s) => s.streamingIntroduction);
  const conclusion = useRoutesStore((s) => s.streamingConclusion);
  const narratives = useRoutesStore((s) => s.streamingNarratives);
  const error = useRoutesStore((s) => s.streamingError);

  const hasStops = stops.length > 0;
  const hasTitle = !!title;

  return (
    <div className="rounded-2xl border border-stone-200/60 bg-white p-6 sm:p-8 shadow-sm space-y-6">
      {/* Pipeline steps */}
      {steps.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {steps.map((s) => (
            <StepBadge key={s.step} step={s} />
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg bg-red-50 border border-red-200 p-4">
          <p className="text-sm text-red-700">{error}</p>
        </div>
      )}

      {/* Title */}
      {hasTitle && (
        <div className="animate-fade-in">
          <h2 className="text-2xl font-bold text-stone-900">{title}</h2>
        </div>
      )}

      {/* Introduction */}
      {introduction && (
        <p className="text-stone-600 leading-relaxed text-sm animate-fade-in">
          {introduction}
        </p>
      )}

      {/* Stops */}
      {hasStops && (
        <div className="space-y-5">
          {stops.map((stop) => {
            const narrative = narratives[stop.order];
            return (
              <div key={stop.order} className="space-y-3 animate-fade-in">
                {narrative ? (
                  <p className="text-sm text-stone-600 leading-relaxed px-1 animate-fade-in">
                    {narrative}
                  </p>
                ) : (
                  <NarrativeSpinner />
                )}
                <RouteStopCard stop={stop} />
              </div>
            );
          })}
        </div>
      )}

      {/* Pending stops skeleton */}
      {!hasStops && steps.length > 0 && !error && (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <SkeletonStopCard key={i} order={i} />
          ))}
        </div>
      )}

      {/* Conclusion */}
      {conclusion ? (
        <p className="text-stone-600 leading-relaxed text-sm italic animate-fade-in">
          {conclusion}
        </p>
      ) : hasStops && !error ? (
        <div className="flex items-center gap-2 py-2">
          <svg className="w-3.5 h-3.5 animate-spin text-green-500" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-xs text-stone-400 italic">Generando conclusion...</span>
        </div>
      ) : null}
    </div>
  );
}
