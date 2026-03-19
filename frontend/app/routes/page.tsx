"use client";

import { useEffect } from "react";
import { useRoutesStore } from "@/store/routes";
import { RouteSmartInput } from "@/components/routes/RouteSmartInput";
import { RouteResult } from "@/components/routes/RouteResult";
import { RouteCard } from "@/components/routes/RouteCard";
import { FilterChipsBase } from "@/components/shared/FilterChips";
import { FilterSidebarBase } from "@/components/shared/FilterSidebar";

function NumStopsSlider() {
  const numStops = useRoutesStore((s) => s.numStops);
  const setNumStops = useRoutesStore((s) => s.setNumStops);

  return (
    <div className="border-t border-stone-100 pt-4">
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium text-stone-700 text-sm">Numero de paradas</span>
        <span className="text-sm font-semibold text-amber-600 tabular-nums">{numStops}</span>
      </div>
      <input
        type="range"
        min={2}
        max={15}
        value={numStops}
        onChange={(e) => setNumStops(Number(e.target.value))}
        className="w-full h-1.5 bg-stone-200 rounded-full appearance-none cursor-pointer accent-amber-500"
      />
      <div className="flex justify-between text-xs text-stone-400 mt-1">
        <span>2</span>
        <span>15</span>
      </div>
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
      extraContent={<NumStopsSlider />}
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

          <RouteSmartInput />
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
