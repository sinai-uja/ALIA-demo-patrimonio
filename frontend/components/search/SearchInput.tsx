"use client";

import { useCallback } from "react";
import { useSearchStore } from "@/store/search";
import {
  SmartInput,
  HERITAGE_TYPE_LABELS,
  type EntityInfo,
  type ActiveFilter,
} from "@/components/shared/SmartInput";

export function SearchInput() {
  const query = useSearchStore((s) => s.query);
  const setQuery = useSearchStore((s) => s.setQuery);
  const syncFiltersWithQuery = useSearchStore((s) => s.syncFiltersWithQuery);
  const performSearch = useSearchStore((s) => s.performSearch);
  const fetchSuggestions = useSearchStore((s) => s.fetchSuggestions);
  const suggestions = useSearchStore((s) => s.suggestions);
  const detectedEntities = useSearchStore((s) => s.detectedEntities);
  const activeFilters = useSearchStore((s) => s.activeFilters);
  const addFilter = useSearchStore((s) => s.addFilter);
  const clearSuggestions = useSearchStore((s) => s.clearSuggestions);
  const loading = useSearchStore((s) => s.loading);

  const handleQueryChange = useCallback(
    (value: string) => {
      setQuery(value);
      syncFiltersWithQuery(value);
    },
    [setQuery, syncFiltersWithQuery],
  );

  const handleEntitySelect = useCallback(
    (entity: EntityInfo) => {
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

      addFilter({
        type: filterType,
        value: entity.value,
        label,
        matchedText: entity.matchedText,
      });
    },
    [addFilter],
  );

  return (
    <SmartInput
      query={query}
      onQueryChange={handleQueryChange}
      onSubmit={performSearch}
      detectedEntities={detectedEntities}
      activeFilters={activeFilters}
      suggestions={suggestions}
      loading={loading}
      onEntitySelect={handleEntitySelect}
      onFetchSuggestions={fetchSuggestions}
      onClearSuggestions={clearSuggestions}
      placeholder="Buscar en el patrimonio historico andaluz..."
      submitLabel="Buscar"
      submitSuffix={<span className="text-stone-400"> por similaridad</span>}
    />
  );
}
