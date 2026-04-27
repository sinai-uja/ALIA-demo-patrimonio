"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuthStore } from "@/store/auth";
import { traces, admin } from "@/lib/api";
import { minDelay } from "@/lib/minDelay";
import TraceDetail, { formatPipelineLabel } from "@/components/admin/TraceDetail";
import type { TraceSummary, TraceListResponse } from "@/lib/api";

const TYPE_OPTIONS = [
  { value: "", label: "Todos" },
  { value: "search", label: "Busqueda" },
  { value: "route", label: "Ruta" },
];

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

function formatDuration(ms: number | null): string {
  if (ms == null) return "-";
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${ms}ms`;
}

function Pagination({
  page,
  totalPages,
  loading,
  onPageChange,
}: {
  page: number;
  totalPages: number;
  loading: boolean;
  onPageChange: (p: number) => void;
}) {
  const pages = new Set<number>();
  pages.add(1);
  pages.add(totalPages);
  for (let i = Math.max(1, page - 1); i <= Math.min(totalPages, page + 1); i++) {
    pages.add(i);
  }
  const sorted = [...pages].sort((a, b) => a - b);
  const items: (number | "ellipsis")[] = [];
  for (let i = 0; i < sorted.length; i++) {
    if (i > 0 && sorted[i] - sorted[i - 1] > 1) items.push("ellipsis");
    items.push(sorted[i]);
  }

  return (
    <nav className="flex items-center justify-center gap-1 pt-2 pb-2" aria-label="Paginacion">
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1 || loading}
        className="px-2 py-1 rounded text-xs text-stone-500 hover:bg-stone-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        aria-label="Pagina anterior"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
        </svg>
      </button>
      {items.map((item, idx) =>
        item === "ellipsis" ? (
          <span key={`e-${idx}`} className="px-1 text-xs text-stone-300">...</span>
        ) : (
          <button
            key={item}
            onClick={() => onPageChange(item)}
            disabled={loading || item === page}
            className={`min-w-[2rem] px-2 py-1 rounded text-xs font-medium transition-colors ${
              item === page
                ? "bg-green-600 text-white cursor-default"
                : "text-stone-500 hover:bg-stone-100"
            } disabled:cursor-not-allowed`}
          >
            {item}
          </button>
        ),
      )}
      <button
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages || loading}
        className="px-2 py-1 rounded text-xs text-stone-500 hover:bg-stone-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        aria-label="Pagina siguiente"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
        </svg>
      </button>
    </nav>
  );
}

export default function TracesPage() {
  const router = useRouter();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const hydrated = useAuthStore((s) => s.hydrated);
  const profileType = useAuthStore((s) => s.profileType);
  const currentUsername = useAuthStore((s) => s.username);

  // Filters
  const [typeFilter, setTypeFilter] = useState("");
  const [since, setSince] = useState("");
  const [until, setUntil] = useState("");
  const [queryFilter, setQueryFilter] = useState("");
  const [userFilter, setUserFilter] = useState("");
  // Users list for dropdown
  const [users, setUsers] = useState<{ id: string; username: string; profile_type: string | null }[]>([]);
  // Data
  const [data, setData] = useState<TraceListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);

  // Detail expansion
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // Auth protection
  useEffect(() => {
    if (!hydrated) return;
    if (!isAuthenticated) { router.replace("/"); return; }
    if (currentUsername !== null && profileType !== "admin") router.replace("/");
  }, [hydrated, isAuthenticated, currentUsername, profileType, router]);

  // Load non-admin users for filter dropdown
  useEffect(() => {
    if (!hydrated || !isAuthenticated || profileType !== "admin") return;
    admin.listUsers().then((list) => {
      // Show: current admin (myself) + all non-admin users
      const me = list.find((u: { username: string }) => u.username === currentUsername);
      const others = list.filter((u: { profile_type: string | null; username: string }) =>
        u.profile_type !== "admin" || u.username === currentUsername
      );
      // Put myself first, then the rest (excluding duplicates)
      const ordered = me
        ? [me, ...others.filter((u: { id: string }) => u.id !== me.id)]
        : others;
      setUsers(ordered);
    }).catch(() => {});
  }, [hydrated, isAuthenticated, profileType, currentUsername]);

  const fetchTraces = useCallback(async (p: number) => {
    setLoading(true);
    setError(null);
    try {
      const result = await minDelay(
        traces.list({
          type: typeFilter || undefined,
          since: since || undefined,
          until: until || undefined,
          query: queryFilter || undefined,
          user_id: userFilter || undefined,
          page: p,
          page_size: 20,
        })
      );
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al cargar trazas");
    } finally {
      setLoading(false);
    }
  }, [typeFilter, since, until, queryFilter, userFilter]);

  // Fetch on mount and when filters change
  useEffect(() => {
    if (!hydrated || !isAuthenticated || profileType !== "admin") return;
    setPage(1);
    fetchTraces(1);
  }, [hydrated, isAuthenticated, profileType, fetchTraces]);

  function handlePageChange(p: number) {
    setPage(p);
    setExpandedId(null);
    fetchTraces(p);
  }

  function handleRowClick(id: string) {
    setExpandedId((prev) => (prev === id ? null : id));
  }

  if (!hydrated || !isAuthenticated || profileType !== "admin") {
    return null;
  }

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      {/* Admin navigation tabs */}
      <div className="mb-6 flex items-center gap-1">
        <Link
          href="/admin"
          className="rounded-lg px-4 py-1.5 text-sm font-medium text-stone-500 hover:text-stone-800 hover:bg-stone-100 transition-colors"
        >
          Gestion de usuarios
        </Link>
        <span className="rounded-lg bg-green-50 px-4 py-1.5 text-sm font-medium text-green-800">
          Trazabilidad
        </span>
      </div>

      {/* Filters */}
      <div className="rounded-xl border border-stone-200/60 bg-white shadow-sm overflow-hidden mb-6">
        <div className="px-5 py-4 border-b border-stone-200">
          <h2 className="text-sm font-semibold text-stone-900">Filtros</h2>
        </div>
        <div className="px-5 py-4 space-y-4">
          {/* Type chips */}
          <div className="space-y-1.5">
            <label className="block text-xs font-medium text-stone-500">Tipo</label>
            <div className="flex flex-wrap gap-1.5">
              {TYPE_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setTypeFilter(opt.value)}
                  className={`rounded-full px-3 py-1 text-xs font-medium transition-colors ${
                    typeFilter === opt.value
                      ? "bg-green-600 text-white"
                      : "bg-stone-100 text-stone-600 hover:bg-stone-200"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Second row: dates, query, user */}
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <div className="space-y-1.5">
              <label htmlFor="trace-since" className="block text-xs font-medium text-stone-500">Desde</label>
              <input
                id="trace-since"
                type="date"
                value={since}
                onChange={(e) => setSince(e.target.value)}
                className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-900 focus:border-green-600 focus:outline-none focus:ring-2 focus:ring-green-600/20"
              />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="trace-until" className="block text-xs font-medium text-stone-500">Hasta</label>
              <input
                id="trace-until"
                type="date"
                value={until}
                onChange={(e) => setUntil(e.target.value)}
                className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-900 focus:border-green-600 focus:outline-none focus:ring-2 focus:ring-green-600/20"
              />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="trace-query" className="block text-xs font-medium text-stone-500">Query</label>
              <input
                id="trace-query"
                type="text"
                value={queryFilter}
                onChange={(e) => setQueryFilter(e.target.value)}
                placeholder="Buscar en queries..."
                className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-900 placeholder:text-stone-400 focus:border-green-600 focus:outline-none focus:ring-2 focus:ring-green-600/20"
              />
            </div>
            <div className="space-y-1.5">
              <label htmlFor="trace-user" className="block text-xs font-medium text-stone-500">Usuario</label>
              <select
                id="trace-user"
                value={userFilter}
                onChange={(e) => setUserFilter(e.target.value)}
                className="w-full rounded-lg border border-stone-300 px-3 py-2 text-sm text-stone-900 focus:border-green-600 focus:outline-none focus:ring-2 focus:ring-green-600/20"
              >
                <option value="">Todos</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>{u.username}{u.profile_type ? ` (${u.profile_type})` : ""}</option>
                ))}
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Results */}
      <div className="rounded-xl border border-stone-200/60 bg-white shadow-sm overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-stone-200">
          <h1 className="text-sm font-semibold text-stone-900">Trazas</h1>
          {data && (
            <span className="text-xs text-stone-400">
              {data.total} resultado{data.total !== 1 ? "s" : ""}
            </span>
          )}
        </div>

        {error && (
          <div className="border-b border-red-100 bg-red-50 px-5 py-2.5 text-xs text-red-700">
            {error}
          </div>
        )}

        {loading ? (
          <div className="flex flex-col items-center justify-center py-16 gap-3">
            <div className="h-6 w-6 animate-spin rounded-full border-2 border-stone-300 border-t-green-600" />
            <span className="text-sm text-stone-400">Cargando trazas...</span>
          </div>
        ) : data && data.traces.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center">
            <svg className="w-12 h-12 text-stone-200 mb-3" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
            </svg>
            <p className="text-stone-500 text-sm font-medium">No se encontraron trazas</p>
            <p className="text-stone-400 text-xs mt-1">Prueba con otros filtros</p>
          </div>
        ) : data ? (
          <>
            {/* Desktop table */}
            <div className="hidden lg:block overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-stone-200 bg-stone-50">
                    <th className="px-5 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-stone-400">Fecha</th>
                    <th className="px-5 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-stone-400">Usuario</th>
                    <th className="px-5 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-stone-400">Perfil</th>
                    <th className="px-5 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-stone-400">Tipo</th>
                    <th className="px-5 py-2.5 text-left text-[11px] font-semibold uppercase tracking-wider text-stone-400">Query</th>
                    <th className="px-5 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-stone-400">Resultados</th>
                    <th className="px-5 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-stone-400">Top Score</th>
                    <th className="px-5 py-2.5 text-right text-[11px] font-semibold uppercase tracking-wider text-stone-400">Duracion</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stone-100">
                  {data.traces.map((trace) => (
                    <TraceRow
                      key={trace.id}
                      trace={trace}
                      expanded={expandedId === trace.id}
                      onClick={() => handleRowClick(trace.id)}
                    />
                  ))}
                </tbody>
              </table>
            </div>

            {/* Mobile cards */}
            <div className="lg:hidden divide-y divide-stone-100">
              {data.traces.map((trace) => (
                <TraceCard
                  key={trace.id}
                  trace={trace}
                  expanded={expandedId === trace.id}
                  onClick={() => handleRowClick(trace.id)}
                />
              ))}
            </div>

            {/* Pagination */}
            <div className="border-t border-stone-200 px-5 py-3">
              <Pagination
                page={page}
                totalPages={data.total_pages}
                loading={loading}
                onPageChange={handlePageChange}
              />
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}

function TraceRow({
  trace,
  expanded,
  onClick,
}: {
  trace: TraceSummary;
  expanded: boolean;
  onClick: () => void;
}) {
  const { label: typeLabel, className: typeBadge } = formatPipelineLabel(
    trace.execution_type,
    trace.pipeline_mode,
  );

  return (
    <>
      <tr
        onClick={onClick}
        className={`cursor-pointer transition-colors ${expanded ? "bg-stone-50" : "hover:bg-stone-50/50"}`}
      >
        <td className="px-5 py-3 text-xs text-stone-600 tabular-nums whitespace-nowrap">
          {formatDate(trace.created_at)}
        </td>
        <td className="px-5 py-3">
          <span className="text-xs font-medium text-stone-900">{trace.username}</span>
        </td>
        <td className="px-5 py-3">
          <span className="text-xs text-stone-500 capitalize">{trace.user_profile_type ?? "-"}</span>
        </td>
        <td className="px-5 py-3">
          <span className={`inline-block rounded-full px-2.5 py-0.5 text-[11px] font-medium ${typeBadge}`}>
            {typeLabel}
          </span>
        </td>
        <td className="px-5 py-3 max-w-[200px]">
          <span className="text-xs text-stone-700 truncate block">{trace.query}</span>
        </td>
        <td className="px-5 py-3 text-right text-xs text-stone-600 tabular-nums">
          {trace.total_results}
        </td>
        <td className="px-5 py-3 text-right text-xs text-stone-600 tabular-nums font-mono">
          {trace.top_score != null ? trace.top_score.toFixed(4) : "-"}
        </td>
        <td className="px-5 py-3 text-right text-xs text-stone-600 tabular-nums whitespace-nowrap">
          {formatDuration(trace.elapsed_ms)}
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={8} className="p-0">
            <TraceDetail traceId={trace.id} />
          </td>
        </tr>
      )}
    </>
  );
}

function TraceCard({
  trace,
  expanded,
  onClick,
}: {
  trace: TraceSummary;
  expanded: boolean;
  onClick: () => void;
}) {
  const { label: typeLabel, className: typeBadge } = formatPipelineLabel(
    trace.execution_type,
    trace.pipeline_mode,
  );

  return (
    <div>
      <button
        onClick={onClick}
        className={`w-full text-left px-5 py-4 transition-colors ${expanded ? "bg-stone-50" : "hover:bg-stone-50/50"}`}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 flex-1 space-y-1.5">
            <p className="text-xs text-stone-700 font-medium truncate">{trace.query}</p>
            <div className="flex flex-wrap items-center gap-2">
              <span className={`inline-block rounded-full px-2.5 py-0.5 text-[11px] font-medium ${typeBadge}`}>
                {typeLabel}
              </span>
              <span className="text-[11px] text-stone-400">{trace.username}</span>
              <span className="text-[11px] text-stone-400 tabular-nums">{formatDate(trace.created_at)}</span>
            </div>
            <div className="flex items-center gap-3 text-[11px] text-stone-500">
              <span>{trace.total_results} resultados</span>
              <span>{formatDuration(trace.elapsed_ms)}</span>
            </div>
          </div>
          <svg
            className={`h-4 w-4 shrink-0 text-stone-400 transition-transform ${expanded ? "rotate-90" : ""}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
          </svg>
        </div>
      </button>
      {expanded && <TraceDetail traceId={trace.id} />}
    </div>
  );
}
