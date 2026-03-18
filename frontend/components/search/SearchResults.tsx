"use client";

import { useSearchStore } from "@/store/search";
import { SearchResultCard } from "./SearchResultCard";

export function SearchResults() {
  const results = useSearchStore((s) => s.results);
  const totalResults = useSearchStore((s) => s.totalResults);
  const loading = useSearchStore((s) => s.loading);
  const hasSearched = useSearchStore((s) => s.hasSearched);

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16 gap-3">
        <svg className="w-8 h-8 animate-spin text-amber-500" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
        </svg>
        <p className="text-sm text-stone-400">Buscando por similaridad...</p>
      </div>
    );
  }

  if (!hasSearched) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <svg className="w-16 h-16 text-stone-200 mb-4" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
        </svg>
        <p className="text-stone-400 text-sm">
          Escribe una consulta para buscar en el patrimonio historico andaluz
        </p>
        <p className="text-stone-300 text-xs mt-1">
          Los resultados se ordenaran por similaridad semantica
        </p>
      </div>
    );
  }

  if (results.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <svg className="w-12 h-12 text-stone-200 mb-3" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
        </svg>
        <p className="text-stone-500 text-sm font-medium">Sin resultados</p>
        <p className="text-stone-400 text-xs mt-1">
          Prueba con otros terminos o quita algun filtro
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-xs text-stone-400">
        {totalResults} resultado{totalResults !== 1 ? "s" : ""} ordenados por similaridad
      </p>
      <div className="space-y-3">
        {results.map((r, i) => (
          <SearchResultCard key={r.chunk_id} result={r} rank={i + 1} />
        ))}
      </div>
    </div>
  );
}
