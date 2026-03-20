"use client";

import { useEffect } from "react";
import { useRoutesStore } from "@/store/routes";
import { RouteSmartInput } from "@/components/routes/RouteSmartInput";
import { RouteResult } from "@/components/routes/RouteResult";
import { RouteCard } from "@/components/routes/RouteCard";
import { FilterChipsBase } from "@/components/shared/FilterChips";
import { FilterSidebarBase } from "@/components/shared/FilterSidebar";

function NumStopsSelector() {
  const numStops = useRoutesStore((s) => s.numStops);
  const setNumStops = useRoutesStore((s) => s.setNumStops);

  return (
    <div className="flex items-center gap-1 border-l border-stone-200 pl-3 ml-1 shrink-0">
      <svg className="w-4 h-4 text-stone-400 shrink-0 mr-0.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z" />
      </svg>
      <button
        type="button"
        onClick={() => setNumStops(Math.max(2, numStops - 1))}
        disabled={numStops <= 2}
        className="w-6 h-6 rounded-md text-stone-400 flex items-center justify-center hover:text-stone-600 hover:bg-stone-100 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14" />
        </svg>
      </button>
      <span className="w-5 text-center text-sm font-semibold text-amber-600 tabular-nums select-none">
        {numStops}
      </span>
      <button
        type="button"
        onClick={() => setNumStops(Math.min(15, numStops + 1))}
        disabled={numStops >= 15}
        className="w-6 h-6 rounded-md text-stone-400 flex items-center justify-center hover:text-stone-600 hover:bg-stone-100 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
        </svg>
      </button>
    </div>
  );
}

function RoutesFilterSidebar() {
  const activeFilters = useRoutesStore((s) => s.activeFilters);
  const filterValues = useRoutesStore((s) => s.filterValues);
  const addFilter = useRoutesStore((s) => s.addFilter);
  const removeFilter = useRoutesStore((s) => s.removeFilter);
  const clearFilters = useRoutesStore((s) => s.clearFilters);

  return (
    <FilterSidebarBase
      filterValues={filterValues}
      activeFilters={activeFilters}
      onAddFilter={addFilter}
      onRemoveFilter={removeFilter}
      onClearAll={clearFilters}
      extraContent={undefined}
    />
  );
}

function RoutesFilterChips() {
  const activeFilters = useRoutesStore((s) => s.activeFilters);
  const removeFilter = useRoutesStore((s) => s.removeFilter);
  const clearFilters = useRoutesStore((s) => s.clearFilters);

  return (
    <FilterChipsBase
      activeFilters={activeFilters}
      onRemoveFilter={removeFilter}
      onClearAll={clearFilters}
    />
  );
}

export default function RoutesPage() {
  const loadRoutes = useRoutesStore((s) => s.loadRoutes);
  const loadFilterValues = useRoutesStore((s) => s.loadFilterValues);
  const routes = useRoutesStore((s) => s.routes);
  const generatedRoute = useRoutesStore((s) => s.generatedRoute);
  const generating = useRoutesStore((s) => s.generating);
  const loading = useRoutesStore((s) => s.loading);

  useEffect(() => {
    loadRoutes();
    loadFilterValues();
  }, [loadRoutes, loadFilterValues]);

  return (
    <div className="relative h-[calc(100vh-3.625rem)] overflow-hidden">
      {/* Sidebar */}
      <aside className="absolute left-0 top-0 bottom-0 w-72 z-10 border-r border-stone-200/60 bg-white overflow-y-auto">
        <RoutesFilterSidebar />
      </aside>

      {/* Main content */}
      <div className="absolute top-0 bottom-0 left-80 right-0 overflow-y-auto">
        <div className="max-w-4xl mx-auto px-6 pt-6 pb-8 space-y-6">
          <div>
            <h1 className="text-3xl font-bold text-stone-900">Rutas Virtuales</h1>
            <p className="text-stone-500 mt-1">
              Planifica una ruta patrimonial por Andalucia
            </p>
          </div>

          <RouteSmartInput numStopsSelector={<NumStopsSelector />} />
          <RoutesFilterChips />

          {/* Generation spinner */}
          {generating && (
            <div className="flex items-center justify-center gap-3 py-8">
              <svg className="w-5 h-5 animate-spin text-amber-500" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              <span className="text-sm text-stone-500">Generando ruta...</span>
            </div>
          )}

          {/* Generated route result */}
          {generatedRoute && !generating && (
            <RouteResult route={generatedRoute} />
          )}

          {/* Previous routes */}
          {routes.length > 0 && (
            <div className="space-y-4">
              <h2 className="text-xl font-semibold text-stone-800">Rutas anteriores</h2>
              <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
                {routes.map((r) => (
                  <RouteCard key={r.id} route={r} />
                ))}
              </div>
            </div>
          )}

          {/* Empty state */}
          {routes.length === 0 && !generatedRoute && !generating && !loading && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <svg className="w-16 h-16 text-stone-200 mb-4" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498 4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 0 0-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0Z" />
              </svg>
              <p className="text-stone-400 text-sm">
                Describe una ruta para explorar el patrimonio historico andaluz
              </p>
              <p className="text-stone-300 text-xs mt-1">
                Se generara una ruta personalizada con paradas y narrativa
              </p>
            </div>
          )}

          {/* Loading routes list */}
          {loading && !generating && (
            <div className="flex justify-center py-8">
              <div className="flex gap-1">
                <span className="typing-dot h-2 w-2 rounded-full bg-amber-400" />
                <span className="typing-dot h-2 w-2 rounded-full bg-amber-400" />
                <span className="typing-dot h-2 w-2 rounded-full bg-amber-400" />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
