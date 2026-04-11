"use client";

import { useEffect, useState } from "react";
import { traces } from "@/lib/api";
import type { TraceDetail as TraceDetailType, TracePipelineStep, TraceResultItem } from "@/lib/api";

function ResultFeedbackIcon({ value }: { value: number }) {
  if (value === 1) {
    return (
      <span className="inline-flex items-center text-green-600" title="Feedback positivo">
        <svg className="h-3.5 w-3.5" fill="currentColor" viewBox="0 0 20 20">
          <path d="M2 10.5a1.5 1.5 0 1 1 3 0v6a1.5 1.5 0 0 1-3 0v-6ZM6 10.333v5.43a2 2 0 0 0 1.106 1.79l.05.025A4 4 0 0 0 8.943 18h5.416a2 2 0 0 0 1.962-1.608l1.2-6A2 2 0 0 0 15.56 8H12V4a2 2 0 0 0-2-2 1 1 0 0 0-1 1v.667a4 4 0 0 1-.8 2.4L6.8 7.933a4 4 0 0 0-.8 2.4Z" />
        </svg>
      </span>
    );
  }
  if (value === -1) {
    return (
      <span className="inline-flex items-center text-red-600" title="Feedback negativo">
        <svg className="h-3.5 w-3.5 rotate-180" fill="currentColor" viewBox="0 0 20 20">
          <path d="M2 10.5a1.5 1.5 0 1 1 3 0v6a1.5 1.5 0 0 1-3 0v-6ZM6 10.333v5.43a2 2 0 0 0 1.106 1.79l.05.025A4 4 0 0 0 8.943 18h5.416a2 2 0 0 0 1.962-1.608l1.2-6A2 2 0 0 0 15.56 8H12V4a2 2 0 0 0-2-2 1 1 0 0 0-1 1v.667a4 4 0 0 1-.8 2.4L6.8 7.933a4 4 0 0 0-.8 2.4Z" />
        </svg>
      </span>
    );
  }
  return null;
}

function StepResults({ results, label, resultFeedbacks }: { results: TraceResultItem[]; label: string; resultFeedbacks?: Record<string, number> | null }) {
  const [expanded, setExpanded] = useState(false);
  const [showAll, setShowAll] = useState(false);

  if (!results || results.length === 0) return null;

  const visible = showAll ? results : results.slice(0, 5);

  return (
    <div className="mt-2">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-1.5 text-xs font-medium text-stone-500 hover:text-stone-700 transition-colors"
      >
        <svg
          className={`h-3 w-3 transition-transform ${expanded ? "rotate-90" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
        </svg>
        {label} ({results.length})
      </button>
      {expanded && (
        <div className="mt-1.5 space-y-1 pl-4">
          {visible.map((r, i) => {
            const fb = r.document_id && resultFeedbacks ? resultFeedbacks[r.document_id] : undefined;
            return (
              <div key={i} className="flex items-center gap-2 text-xs text-stone-600">
                <span className="shrink-0 tabular-nums text-stone-400">#{r.rank}</span>
                <span className="shrink-0 tabular-nums font-mono text-[11px]">
                  {r.score?.toFixed(4)}
                </span>
                <span className="truncate font-medium">{r.title}</span>
                <span className="shrink-0 text-stone-400">{r.heritage_type}</span>
                <span className="shrink-0 text-stone-400">{r.province}</span>
                {fb !== undefined && <ResultFeedbackIcon value={fb} />}
              </div>
            );
          })}
          {results.length > 5 && !showAll && (
            <button
              onClick={() => setShowAll(true)}
              className="text-xs font-medium text-green-700 hover:text-green-800 transition-colors"
            >
              Ver todos ({results.length})
            </button>
          )}
        </div>
      )}
    </div>
  );
}


function LlmResponse({ response }: { response: string }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="mt-2">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-1.5 text-xs font-medium text-stone-500 hover:text-stone-700 transition-colors"
      >
        <svg
          className={`h-3 w-3 transition-transform ${expanded ? "rotate-90" : ""}`}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
        </svg>
        Ver respuesta ({response.length} chars)
      </button>
      {expanded && (
        <div className="mt-1.5 rounded-lg bg-stone-50 p-3 text-xs text-stone-700 whitespace-pre-wrap border border-stone-100 max-h-64 overflow-y-auto">
          {response}
        </div>
      )}
    </div>
  );
}

const STEP_LABELS: Record<string, string> = {
  embedding: "Embedding",
  vector_search: "Vector Search",
  text_search: "Text Search",
  fusion: "Fusión RRF",
  reranker: "Neural Reranker",
  results: "Resultados finales",
  query_extraction: "Extracción de query (LLM)",
  rag_query: "Consulta RAG",
  stop_selection: "Selección de paradas",
  heritage_asset_lookup: "Lookup assets patrimoniales",
  narrative_generation: "Generación narrativa (LLM)",
  route_build: "Construcción de ruta",
};

function buildStepSummary(step: TracePipelineStep): string {
  const input = step.input || {};
  const output = step.output || {};
  switch (step.step) {
    case "embedding":
      return `"${String(input.text ?? "").slice(0, 60)}" (${input.chars ?? "?"} chars) → ${output.dim ?? "?"}‑dim vector`;
    case "vector_search":
      return `top_k=${input.top_k ?? "?"}, filtros: ${input.filters ?? "ninguno"} → ${output.count ?? "?"} resultados (top: ${output.top_score != null ? Number(output.top_score).toFixed(4) : "-"})`;
    case "text_search":
      return `query: "${String(input.query ?? "").slice(0, 60)}", top_k=${input.top_k ?? "?"} → ${output.count ?? "?"} resultados`;
    case "fusion":
      return `vector: ${input.vector ?? "?"}, text: ${input.text ?? "?"} → fusionados: ${output.fused ?? "?"}, filtrados: ${output.filtered ?? "?"}`;
    case "reranker":
      return `${input.candidates ?? "?"} candidatos → ${output.count ?? "?"} resultados (top: ${output.top_score != null ? Number(output.top_score).toFixed(4) : "-"})`;
    case "results":
      return `${output.total_results ?? "?"} resultados, página ${output.page ?? "?"}/${output.total_pages ?? "?"}`;
    case "query_extraction":
      return `"${String(input.original_query ?? "").slice(0, 80)}" → "${String(output.extracted_query ?? "").slice(0, 80)}"`;
    case "rag_query":
      return `query: "${String(input.query ?? "").slice(0, 60)}", top_k=${input.top_k ?? "?"} → ${output.chunks_returned ?? "?"} chunks`;
    case "stop_selection":
      return `${input.candidates ?? "?"} candidatos → ${output.selected ?? "?"} paradas seleccionadas`;
    case "heritage_asset_lookup":
      return `${input.asset_ids ?? "?"} assets solicitados → ${output.previews_found ?? "?"} encontrados`;
    case "narrative_generation": {
      const method = output.parse_method ? ` [${output.parse_method}]` : "";
      return `"${String(output.title ?? "").slice(0, 60)}" — ${output.segments ?? "?"} segmentos, ${output.narrative_chars ?? "?"} chars${method}`;
    }
    case "route_build":
      return `${output.stops ?? "?"} paradas, ${output.province ?? "?"}`;
    default:
      return Object.entries(output).map(([k, v]) => `${k}: ${v}`).join(", ") || "";
  }
}

function ExpandableText({ label, text }: { label: string; text: string }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="mt-1.5">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-1.5 text-xs font-medium text-stone-500 hover:text-stone-700 transition-colors"
      >
        <svg
          className={`h-3 w-3 transition-transform ${expanded ? "rotate-90" : ""}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
        </svg>
        {label}
      </button>
      {expanded && (
        <pre className="mt-1.5 rounded-lg bg-stone-50 p-3 text-[11px] text-stone-600 overflow-x-auto border border-stone-100 max-h-64 overflow-y-auto whitespace-pre-wrap">
          {text}
        </pre>
      )}
    </div>
  );
}

function PipelineStep({ step, isLast, resultFeedbacks }: { step: TracePipelineStep; isLast: boolean; resultFeedbacks?: Record<string, number> | null }) {
  const label = STEP_LABELS[step.step] ?? step.step;
  const summary = buildStepSummary(step);
  const input = step.input || {};
  const output = step.output || {};

  return (
    <div className="relative flex gap-3">
      {/* Timeline line */}
      <div className="flex flex-col items-center">
        <div className="mt-1 h-2.5 w-2.5 shrink-0 rounded-full bg-blue-500" />
        {!isLast && <div className="mt-1 w-px flex-1 bg-stone-200" />}
      </div>

      {/* Content */}
      <div className={`flex-1 ${isLast ? "pb-0" : "pb-5"}`}>
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-sm font-medium text-stone-800">{label}</span>
          {step.elapsed_ms != null && (
            <span className="shrink-0 text-xs tabular-nums text-stone-400">
              {step.elapsed_ms >= 1000
                ? `${(step.elapsed_ms / 1000).toFixed(1)}s`
                : `${Math.round(step.elapsed_ms)}ms`}
            </span>
          )}
        </div>
        <p className="mt-0.5 text-xs text-stone-500">{summary}</p>
        {step.results && step.results.length > 0 && (
          <StepResults results={step.results} label="Ver resultados" resultFeedbacks={resultFeedbacks} />
        )}
        {/* Expandable prompts & responses for LLM steps */}
        {typeof input.system_prompt === "string" && (
          <ExpandableText label="Ver system prompt" text={input.system_prompt} />
        )}
        {typeof input.user_prompt === "string" && (
          <ExpandableText label="Ver user prompt" text={input.user_prompt} />
        )}
        {typeof output.raw_response === "string" && (
          <ExpandableText label="Ver respuesta LLM (cruda)" text={output.raw_response} />
        )}
      </div>
    </div>
  );
}

function FeedbackBadge({ feedback, profileType }: { feedback: number | null; profileType: string | null }) {
  if (feedback === 1) {
    return (
      <div className="mt-3 flex items-center gap-2">
        <div className="h-2.5 w-2.5 rounded-full bg-green-500" />
        <span className="text-sm font-medium text-green-700">
          Feedback positivo
        </span>
        {profileType && (
          <span className="text-xs text-stone-400">({profileType})</span>
        )}
      </div>
    );
  }
  if (feedback === -1) {
    return (
      <div className="mt-3 flex items-center gap-2">
        <div className="h-2.5 w-2.5 rounded-full bg-red-500" />
        <span className="text-sm font-medium text-red-700">
          Feedback negativo
        </span>
        {profileType && (
          <span className="text-xs text-stone-400">({profileType})</span>
        )}
      </div>
    );
  }
  return (
    <div className="mt-3 flex items-center gap-2">
      <div className="h-2.5 w-2.5 rounded-full bg-orange-400" />
      <span className="text-sm font-medium text-stone-500">Sin feedback</span>
    </div>
  );
}

interface TraceDetailProps {
  traceId: string;
}

export default function TraceDetail({ traceId }: TraceDetailProps) {
  const [trace, setTrace] = useState<TraceDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    traces
      .get(traceId)
      .then((data) => {
        if (!cancelled) setTrace(data);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Error al cargar traza");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [traceId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="h-5 w-5 animate-spin rounded-full border-2 border-stone-300 border-t-green-600" />
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

  if (!trace) return null;

  return (
    <div className="border-t border-stone-100 bg-stone-50/50 px-5 py-4">
      <div className="grid gap-6 lg:grid-cols-[1fr_auto]">
        {/* Pipeline timeline */}
        <div>
          <h4 className="mb-3 text-xs font-semibold uppercase tracking-wider text-stone-400">
            Pipeline de ejecucion
          </h4>
          <div className="space-y-0">
            {trace.steps && trace.steps.length > 0 ? (
              trace.steps.map((step, i) => (
                <PipelineStep
                  key={i}
                  step={step}
                  isLast={i === trace.steps.length - 1}
                  resultFeedbacks={trace.result_feedbacks}
                />
              ))
            ) : (
              <p className="text-xs text-stone-400">No hay pasos de pipeline registrados</p>
            )}
          </div>

          {/* LLM response */}
          {trace.llm_response && <LlmResponse response={trace.llm_response} />}

          {/* Feedback — only for non-search types (search feedback is per-result) */}
          {trace.execution_type !== "search" && (
            <FeedbackBadge feedback={trace.feedback_value} profileType={trace.user_profile_type} />
          )}
          {/* Per-result feedback summary for search */}
          {trace.execution_type === "search" && trace.result_feedbacks && Object.keys(trace.result_feedbacks).length > 0 && (
            <div className="mt-3 flex items-center gap-2">
              <div className="h-2.5 w-2.5 rounded-full bg-green-500" />
              <span className="text-sm font-medium text-stone-700">
                Feedback en resultados: {Object.values(trace.result_feedbacks).filter(v => v === 1).length} 👍 / {Object.values(trace.result_feedbacks).filter(v => v === -1).length} 👎
              </span>
            </div>
          )}
          {trace.execution_type === "search" && (!trace.result_feedbacks || Object.keys(trace.result_feedbacks).length === 0) && (
            <div className="mt-3 flex items-center gap-2">
              <div className="h-2.5 w-2.5 rounded-full bg-stone-300" />
              <span className="text-sm text-stone-400">Sin feedback en resultados</span>
            </div>
          )}
        </div>

        {/* Metadata sidebar */}
        <div className="w-56 shrink-0 space-y-3">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-stone-400">
            Metadatos
          </h4>
          <dl className="space-y-2 text-xs">
            <div>
              <dt className="text-stone-400">ID</dt>
              <dd className="font-mono text-stone-600 break-all">{trace.id}</dd>
            </div>
            <div>
              <dt className="text-stone-400">Usuario</dt>
              <dd className="text-stone-600">{trace.username}</dd>
            </div>
            <div>
              <dt className="text-stone-400">Perfil</dt>
              <dd className="text-stone-600 capitalize">{trace.user_profile_type ?? "sin perfil"}</dd>
            </div>
            <div>
              <dt className="text-stone-400">Tipo</dt>
              <dd className="text-stone-600 capitalize">{trace.execution_type}</dd>
            </div>
            {trace.filters && Object.keys(trace.filters).length > 0 && (
              <div>
                <dt className="text-stone-400">Filtros</dt>
                <dd className="text-stone-600">
                  {Object.entries(trace.filters).map(([k, v]) => (
                    <span key={k} className="mr-1.5 inline-block rounded bg-stone-100 px-1.5 py-0.5 text-[11px]">
                      {k}={String(v)}
                    </span>
                  ))}
                </dd>
              </div>
            )}
            {trace.elapsed_ms != null && (
              <div>
                <dt className="text-stone-400">Duracion total</dt>
                <dd className="text-stone-600 tabular-nums">
                  {trace.elapsed_ms >= 1000
                    ? `${(trace.elapsed_ms / 1000).toFixed(1)}s`
                    : `${trace.elapsed_ms}ms`}
                </dd>
              </div>
            )}
          </dl>
        </div>
      </div>
    </div>
  );
}
