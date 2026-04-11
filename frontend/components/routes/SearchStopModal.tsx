"use client";

import { useCallback, useEffect, useState } from "react";
import { search, heritage, type SearchResult, type DetectedEntity, type HeritageAsset } from "@/lib/api";
import { type ActiveFilter, collectFilters } from "@/lib/filterUtils";
import {
  SmartInput,
  HERITAGE_TYPE_LABELS,
  type EntityInfo,
} from "@/components/shared/SmartInput";
import { FilterChipsBase } from "@/components/shared/FilterChips";
import { AssetDetailContent } from "@/components/shared/AssetDetailContent";

const HERITAGE_LABELS: Record<string, string> = {
  patrimonio_inmueble: "Inmueble",
  patrimonio_mueble: "Mueble",
  patrimonio_inmaterial: "Inmaterial",
  paisaje_cultural: "Paisaje Cultural",
};

const HERITAGE_COLORS: Record<string, string> = {
  patrimonio_inmueble: "bg-green-100 text-green-700",
  patrimonio_mueble: "bg-purple-100 text-purple-700",
  patrimonio_inmaterial: "bg-teal-100 text-teal-700",
  paisaje_cultural: "bg-sky-100 text-sky-700",
};

function scoreToPercent(score: number): number {
  return Math.max(0, Math.round((1 - score) * 100));
}

function extractAssetId(documentId: string): string {
  return documentId.replace(/^ficha-\w+-/, "");
}

interface SearchStopModalProps {
  onSelect: (documentId: string) => void;
  onClose: () => void;
  adding: boolean;
}

export function SearchStopModal({ onSelect, onClose, adding }: SearchStopModalProps) {
  // ── Local state (isolated from global search store) ──────────────────────
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [searched, setSearched] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  // Pagination state
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [totalResults, setTotalResults] = useState(0);

  // Detail panel state
  const [detailAsset, setDetailAsset] = useState<HeritageAsset | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  // Smart input state
  const [detectedEntities, setDetectedEntities] = useState<DetectedEntity[]>([]);
  const [activeFilters, setActiveFilters] = useState<ActiveFilter[]>([]);

  // ── Escape to close ──────────────────────────────────────────────────────
  useEffect(() => {
    function handleEscape(e: KeyboardEvent) {
      if (e.key === "Escape") {
        if (detailAsset) {
          setDetailAsset(null);
        } else if (!adding) {
          onClose();
        }
      }
    }
    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [onClose, adding, detailAsset]);

  // ── Suggestion fetching (entity detection) ──────────────────────────────
  const fetchSuggestions = useCallback(async (q: string) => {
    if (!q.trim() || q.trim().length < 2) {
      setDetectedEntities([]);
      return;
    }
    try {
      const res = await search.suggestions(q.trim());
      setDetectedEntities(res.detected_entities);
    } catch {
      // ignore
    }
  }, []);

  const clearSuggestions = useCallback(() => {
    // We keep detectedEntities for the overlay highlights;
    // only the dropdown suggestion list is conceptually cleared.
  }, []);

  // ── Query change handler (sync filters with query) ──────────────────────
  const handleQueryChange = useCallback(
    (value: string) => {
      setQuery(value);
      // Remove filters whose matched text is no longer in the query
      setActiveFilters((prev) => {
        if (prev.length === 0) return prev;
        const lower = value.toLowerCase();
        const remaining = prev.filter((f) => {
          if (!f.matchedText) return true;
          return lower.includes(f.matchedText.toLowerCase());
        });
        return remaining.length !== prev.length ? remaining : prev;
      });
    },
    [],
  );

  // ── Entity selection → add filter ───────────────────────────────────────
  const handleEntitySelect = useCallback((entity: EntityInfo) => {
    const typeMap: Record<string, ActiveFilter["type"]> = {
      province: "province",
      municipality: "municipality",
      heritage_type: "heritage_type",
    };
    const filterType = typeMap[entity.entityType];
    if (!filterType) return;

    let label = entity.value;
    if (filterType === "heritage_type") {
      label = HERITAGE_TYPE_LABELS[entity.value] ?? entity.value;
    }

    const newFilter: ActiveFilter = {
      type: filterType,
      value: entity.value,
      label,
      matchedText: entity.matchedText,
    };

    setActiveFilters((prev) => {
      const exists = prev.some((f) => f.type === newFilter.type && f.value === newFilter.value);
      if (exists) return prev;
      return [...prev, newFilter];
    });
  }, []);

  // ── Remove / clear filters ─────────────────────────────────────────────
  const handleRemoveFilter = useCallback((filter: ActiveFilter) => {
    setActiveFilters((prev) =>
      prev.filter((f) => !(f.type === filter.type && f.value === filter.value)),
    );
  }, []);

  const handleClearAllFilters = useCallback(() => {
    setActiveFilters([]);
  }, []);

  // ── Search execution ───────────────────────────────────────────────────
  const executeSearch = useCallback(async (searchPage: number) => {
    const cleanQuery = query.replace(/\s{2,}/g, " ").trim();
    if (!cleanQuery) return;
    setSearching(true);
    setSearched(true);
    try {
      const filters = collectFilters(activeFilters);
      const res = await search.similarity({
        query: cleanQuery,
        page_size: 10,
        page: searchPage,
        ...filters,
      });
      setResults(res.results);
      setPage(res.page);
      setTotalPages(res.total_pages);
      setTotalResults(res.total_results);
    } catch {
      setResults([]);
    } finally {
      setSearching(false);
    }
  }, [query, activeFilters]);

  const handleSearch = useCallback(async () => {
    if (!query.replace(/\s{2,}/g, " ").trim() || searching) return;
    setPage(1);
    setDetailAsset(null);
    await executeSearch(1);
  }, [query, searching, executeSearch]);

  const handlePageChange = useCallback((newPage: number) => {
    if (newPage < 1 || newPage > totalPages || searching) return;
    setDetailAsset(null);
    executeSearch(newPage);
  }, [totalPages, searching, executeSearch]);

  // ── Detail panel ────────────────────────────────────────────────────────
  const openDetail = useCallback(async (documentId: string) => {
    const assetId = extractAssetId(documentId);
    setDetailLoading(true);
    setDetailAsset(null);
    try {
      const asset = await heritage.get(assetId);
      setDetailAsset(asset);
    } catch {
      // ignore
    } finally {
      setDetailLoading(false);
    }
  }, []);

  const closeDetail = useCallback(() => {
    setDetailAsset(null);
    setDetailLoading(false);
  }, []);

  // ── Result selection ───────────────────────────────────────────────────
  const handleSelect = (documentId: string) => {
    setSelectedId(documentId);
    onSelect(documentId);
  };

  const detailOpen = detailAsset !== null || detailLoading;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm"
      onClick={adding ? undefined : onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl w-full max-w-4xl mx-4 flex flex-col h-[calc(100vh-6rem)] animate-in fade-in zoom-in-95 duration-200"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="px-6 pt-6 pb-4 border-b border-stone-100 shrink-0">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-stone-900">Buscar parada</h2>
            <button
              onClick={onClose}
              disabled={adding}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-stone-400 hover:text-stone-600 hover:bg-stone-100 transition-colors disabled:opacity-40"
              aria-label="Cerrar"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Smart input with entity detection */}
          <SmartInput
            query={query}
            onQueryChange={handleQueryChange}
            onSubmit={handleSearch}
            detectedEntities={detectedEntities}
            activeFilters={activeFilters}
            loading={searching}
            onEntitySelect={handleEntitySelect}
            onFetchSuggestions={fetchSuggestions}
            onClearSuggestions={clearSuggestions}
            placeholder="Buscar patrimonio por nombre, tipo, lugar..."
          />

          {/* Filter chips */}
          {activeFilters.length > 0 && (
            <div className="mt-3">
              <FilterChipsBase
                activeFilters={activeFilters}
                onRemoveFilter={handleRemoveFilter}
                onClearAll={handleClearAllFilters}
              />
            </div>
          )}
        </div>

        {/* Body: results list + optional detail panel */}
        <div className="flex-1 flex min-h-0">
          {/* Results column */}
          <div className={`flex flex-col min-h-0 transition-all duration-300 ${detailOpen ? "w-1/2 border-r border-stone-100" : "w-full"}`}>
            <div className="flex-1 overflow-y-auto px-6 py-4">
              {!searched && !searching && (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <svg className="w-12 h-12 text-stone-200 mb-3" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
                  </svg>
                  <p className="text-sm text-stone-400">
                    Busca un bien patrimonial para agregarlo como parada
                  </p>
                </div>
              )}

              {searching && (
                <div className="flex justify-center py-12">
                  <div className="flex gap-1">
                    <span className="typing-dot h-2 w-2 rounded-full bg-green-500" />
                    <span className="typing-dot h-2 w-2 rounded-full bg-green-500" />
                    <span className="typing-dot h-2 w-2 rounded-full bg-green-500" />
                  </div>
                </div>
              )}

              {searched && !searching && results.length === 0 && (
                <div className="flex flex-col items-center justify-center py-12 text-center">
                  <p className="text-sm text-stone-400">
                    No se encontraron resultados para esta busqueda
                  </p>
                </div>
              )}

              {!searching && results.length > 0 && (
                <div className="space-y-2">
                  {results.map((result) => {
                    const typeLabel = HERITAGE_LABELS[result.heritage_type] ?? result.heritage_type;
                    const typeColor = HERITAGE_COLORS[result.heritage_type] ?? "bg-stone-100 text-stone-700";
                    const similarity = scoreToPercent(result.best_score);
                    const isSelected = selectedId === result.document_id;

                    return (
                      <div
                        key={result.document_id}
                        className={`rounded-xl border p-4 transition-all ${
                          isSelected && adding
                            ? "border-green-300 bg-green-50"
                            : "border-stone-200/60 bg-white"
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          {/* Thumbnail */}
                          {result.image_url ? (
                            <img
                              src={result.image_url}
                              alt={result.title}
                              className="w-14 h-14 rounded-lg object-cover bg-stone-100 shrink-0"
                            />
                          ) : (
                            <div className="w-14 h-14 rounded-lg bg-stone-100 flex items-center justify-center shrink-0">
                              <svg className="w-6 h-6 text-stone-300" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0 0 12 9.75c-2.551 0-5.056.2-7.5.582V21" />
                              </svg>
                            </div>
                          )}

                          {/* Content */}
                          <div className="flex-1 min-w-0">
                            <h4 className="font-semibold text-sm text-stone-900 leading-snug line-clamp-1">
                              {result.denomination || result.title}
                            </h4>
                            <div className="flex flex-wrap items-center gap-1.5 mt-1">
                              <span className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${typeColor}`}>
                                {typeLabel}
                              </span>
                              <span className="text-[10px] text-stone-400">
                                {result.municipality ? `${result.municipality}, ` : ""}
                                {result.province}
                              </span>
                            </div>
                          </div>

                          {/* Score + actions (right column) */}
                          <div className="shrink-0 flex flex-col items-center gap-1.5">
                            <span className="text-xs font-semibold text-green-700">{similarity}%</span>
                            <span className="text-[9px] text-stone-400">similitud</span>
                            <button
                              onClick={() => openDetail(result.document_id)}
                              className="text-[10px] font-medium text-stone-500 hover:text-green-700 hover:underline transition-colors"
                            >
                              Ver detalle
                            </button>
                            <button
                              onClick={() => handleSelect(result.document_id)}
                              disabled={adding}
                              className="inline-flex items-center gap-1 rounded-lg bg-green-600 px-2 py-0.5 text-[10px] font-medium text-white hover:bg-green-700 transition-colors disabled:opacity-50 disabled:cursor-wait"
                            >
                              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                                </svg>
                                Añadir
                              </button>
                          </div>
                        </div>

                        {/* Loading indicator when this item is being added */}
                        {isSelected && adding && (
                          <div className="flex items-center gap-2 mt-2 pt-2 border-t border-green-100">
                            <svg className="w-3.5 h-3.5 animate-spin text-green-600" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                            </svg>
                            <span className="text-xs text-green-700">Generando narrativa y agregando parada...</span>
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </div>

            {/* Pagination */}
            {searched && !searching && totalPages > 1 && (
              <div className="shrink-0 px-6 py-3 border-t border-stone-100 flex items-center justify-between">
                <span className="text-xs text-stone-500">
                  {totalResults} resultado{totalResults !== 1 ? "s" : ""}
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handlePageChange(page - 1)}
                    disabled={page <= 1}
                    className="rounded-lg px-2.5 py-1 text-xs font-medium text-stone-600 hover:bg-stone-100 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    Anterior
                  </button>
                  <span className="text-xs text-stone-500">
                    Pagina {page} de {totalPages}
                  </span>
                  <button
                    onClick={() => handlePageChange(page + 1)}
                    disabled={page >= totalPages}
                    className="rounded-lg px-2.5 py-1 text-xs font-medium text-stone-600 hover:bg-stone-100 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
                  >
                    Siguiente
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Detail panel (slides in from right) */}
          {detailOpen && (
            <div className="w-1/2 min-h-0 overflow-y-auto animate-in slide-in-from-right duration-300">
              <AssetDetailContent
                asset={detailAsset}
                onClose={closeDetail}
                loading={detailLoading}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
