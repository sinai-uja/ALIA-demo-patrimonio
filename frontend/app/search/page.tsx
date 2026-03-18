"use client";

import { useEffect } from "react";
import { useSearchStore } from "@/store/search";
import { SearchInput } from "@/components/search/SearchInput";
import { FilterChips } from "@/components/search/FilterChips";
import { SearchResults } from "@/components/search/SearchResults";

export default function SearchPage() {
  const loadFilterValues = useSearchStore((s) => s.loadFilterValues);

  useEffect(() => {
    loadFilterValues();
  }, [loadFilterValues]);

  return (
    <div className="mx-auto max-w-4xl px-6 py-8 space-y-6">
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
  );
}
