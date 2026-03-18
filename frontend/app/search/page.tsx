"use client";

import { useEffect } from "react";
import { useSearchStore } from "@/store/search";
import { SearchInput } from "@/components/search/SearchInput";
import { FilterChips } from "@/components/search/FilterChips";
import { SearchResults } from "@/components/search/SearchResults";
import { FilterSidebar } from "@/components/search/FilterSidebar";
import { AssetDetailPanel } from "@/components/search/AssetDetailPanel";

export default function SearchPage() {
  const loadFilterValues = useSearchStore((s) => s.loadFilterValues);
  const hasDetail = useSearchStore((s) => s.selectedAssetId !== null);

  useEffect(() => {
    loadFilterValues();
  }, [loadFilterValues]);

  return (
    <div className="relative h-[calc(100vh-3.625rem)] overflow-hidden">
      {/* Sidebar */}
      <aside className="absolute left-0 top-0 bottom-0 w-72 z-10 border-r border-stone-200/60 bg-white overflow-y-auto">
        <FilterSidebar />
      </aside>

      {/* Main content — scrolls independently */}
      <div
        className={`absolute top-0 bottom-0 left-80 overflow-y-auto transition-all duration-300 ${
          hasDetail ? "right-[480px]" : "right-0"
        }`}
      >
        <div className="max-w-4xl mx-auto px-6 pt-6 pb-3 space-y-6">
          <div>
            <h1 className="text-3xl font-bold text-stone-900">Busqueda por Similaridad</h1>
            <p className="text-stone-500 mt-1">
              Encuentra bienes patrimoniales mediante busqueda semantica en la base de datos del IAPH
            </p>
          </div>

          <SearchInput />
          <FilterChips />
          <SearchResults />
        </div>
      </div>

      {/* Detail panel */}
      {hasDetail && (
        <aside className="absolute right-0 top-0 bottom-0 w-[480px] z-10">
          <AssetDetailPanel />
        </aside>
      )}
    </div>
  );
}
