"use client";

import { useEffect, useState } from "react";
import { useSearchStore } from "@/store/search";
import { SearchInput } from "@/components/search/SearchInput";
import { FilterChips } from "@/components/search/FilterChips";
import { SearchResults } from "@/components/search/SearchResults";
import { FilterSidebar } from "@/components/search/FilterSidebar";
import { AssetDetailPanel } from "@/components/search/AssetDetailPanel";
import { CollapsibleDrawer } from "@/components/shared/CollapsibleDrawer";
import { minDelay } from "@/lib/minDelay";

export default function SearchPage() {
  const loadFilterValues = useSearchStore((s) => s.loadFilterValues);
  const hasDetail = useSearchStore((s) => s.selectedAssetId !== null);
  const activeFilters = useSearchStore((s) => s.activeFilters);
  const hasSearched = useSearchStore((s) => s.hasSearched);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    minDelay(loadFilterValues()).finally(() => setReady(true));
  }, [loadFilterValues]);

  const filterButton = (
    <button
      onClick={() => setDrawerOpen((v) => !v)}
      className="shrink-0 relative flex h-9 w-9 items-center justify-center rounded-lg border border-stone-200 bg-white text-stone-500 hover:text-stone-700 hover:border-stone-300 transition-colors"
      aria-label={drawerOpen ? "Cerrar filtros" : "Abrir filtros"}
    >
      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 0 1-.659 1.591l-5.432 5.432a2.25 2.25 0 0 0-.659 1.591v2.927a2.25 2.25 0 0 1-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 0 0-.659-1.591L3.659 7.409A2.25 2.25 0 0 1 3 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0 1 12 3Z" />
      </svg>
      {activeFilters.length > 0 && (
        <span className="absolute -top-1 -right-1 flex h-4 w-4 items-center justify-center rounded-full bg-green-600 text-[10px] font-bold text-white">
          {activeFilters.length}
        </span>
      )}
    </button>
  );

  if (!ready) {
    return (
      <div className="flex flex-col items-center justify-center h-[calc(100vh-3.625rem)] gap-3">
        <div className="h-6 w-6 animate-spin rounded-full border-2 border-stone-300 border-t-green-600" />
        <span className="text-sm text-stone-400">Cargando búsqueda...</span>
      </div>
    );
  }

  return (
    <div className="relative h-[calc(100vh-3.625rem)] overflow-hidden">
      {/* Filter drawer */}
      <CollapsibleDrawer open={drawerOpen} width="w-72">
        <div className="overflow-y-auto h-full">
          <FilterSidebar />
        </div>
      </CollapsibleDrawer>

      {/* Main content */}
      <div
        className={`absolute top-0 bottom-0 overflow-y-scroll transition-all duration-300 ${
          drawerOpen ? "left-72" : "left-0"
        } ${hasDetail ? "md:right-[560px]" : "right-0"}`}
      >
        {!hasSearched ? (
          /* Centered empty state */
          <div className="min-h-full flex items-start justify-center px-6 pt-[25vh] pb-8 relative">
            <div className="absolute top-6 left-6">{filterButton}</div>
            <div className="w-full max-w-xl space-y-5">
              <div className="text-center space-y-2">
                <svg className="mx-auto w-12 h-12 text-stone-200" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
                </svg>
                <p className="text-lg font-semibold text-stone-700">Búsqueda por Similaridad</p>
                <p className="text-sm text-stone-400">
                  Escribe una consulta para buscar en el patrimonio histórico andaluz
                </p>
              </div>
              <SearchInput />
              <FilterChips />
            </div>
          </div>
        ) : (
          /* Normal layout with results */
          <div className="max-w-4xl mx-auto px-6 pt-8 pb-3 space-y-6">
            <div className="flex items-start gap-4">
              <div className="mt-2">{filterButton}</div>
              <div className="flex-1 min-w-0">
                <h1 className="text-3xl font-bold tracking-tight text-stone-900">Búsqueda por Similaridad</h1>
                <p className="text-stone-500 mt-1.5 text-sm sm:text-base">
                  Encuentra bienes patrimoniales mediante búsqueda semántica en el catálogo de Patrimonio de Andalucía
                </p>
              </div>
            </div>
            <SearchInput />
            <FilterChips />
            <SearchResults />
          </div>
        )}
      </div>

      {/* Detail panel */}
      {hasDetail && (
        <aside className="fixed inset-0 z-50 md:absolute md:inset-auto md:right-0 md:top-0 md:bottom-0 md:w-[560px] md:z-10">
          <AssetDetailPanel />
        </aside>
      )}
    </div>
  );
}
