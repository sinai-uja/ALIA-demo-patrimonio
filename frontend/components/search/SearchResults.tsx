"use client";

import { useSearchStore } from "@/store/search";
import { SearchResultCard } from "./SearchResultCard";

function Pagination() {
  const page = useSearchStore((s) => s.page);
  const totalPages = useSearchStore((s) => s.totalPages);
  const loading = useSearchStore((s) => s.loading);
  const goToPage = useSearchStore((s) => s.goToPage);

  if (totalPages <= 1) return null;

  // Build visible page numbers: first, last, current +/- 1
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
        onClick={() => goToPage(page - 1)}
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
            onClick={() => goToPage(item)}
            disabled={loading}
            className={`min-w-[2rem] px-2 py-1 rounded text-xs font-medium transition-colors ${
              item === page
                ? "bg-amber-500 text-white"
                : "text-stone-500 hover:bg-stone-100"
            } disabled:cursor-not-allowed`}
          >
            {item}
          </button>
        ),
      )}
      <button
        onClick={() => goToPage(page + 1)}
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

export function SearchResults() {
  const results = useSearchStore((s) => s.results);
  const totalResults = useSearchStore((s) => s.totalResults);
  const page = useSearchStore((s) => s.page);
  const pageSize = useSearchStore((s) => s.pageSize);
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

  const startRank = (page - 1) * pageSize;

  return (
    <div className="space-y-3">
      <p className="text-xs text-stone-400">
        {totalResults} resultado{totalResults !== 1 ? "s" : ""} ordenados por similaridad
      </p>
      <div className="space-y-3">
        {results.map((r, i) => (
          <SearchResultCard key={r.document_id} result={r} rank={startRank + i + 1} />
        ))}
      </div>
      <Pagination />
    </div>
  );
}
