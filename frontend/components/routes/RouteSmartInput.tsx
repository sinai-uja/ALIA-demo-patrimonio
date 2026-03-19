"use client";

import { useCallback } from "react";
import { useRoutesStore } from "@/store/routes";
import {
  SmartInput,
  HERITAGE_TYPE_LABELS,
  type EntityInfo,
  type ActiveFilter,
} from "@/components/shared/SmartInput";

const RouteIcon = (
  <svg
    className="w-5 h-5 text-stone-400"
    fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"
  >
    <path strokeLinecap="round" strokeLinejoin="round" d="M9 6.75V15m6-6v8.25m.503 3.498 4.875-2.437c.381-.19.622-.58.622-1.006V4.82c0-.836-.88-1.38-1.628-1.006l-3.869 1.934c-.317.159-.69.159-1.006 0L9.503 3.252a1.125 1.125 0 0 0-1.006 0L3.622 5.689C3.24 5.88 3 6.27 3 6.695V19.18c0 .836.88 1.38 1.628 1.006l3.869-1.934c.317-.159.69-.159 1.006 0l4.994 2.497c.317.158.69.158 1.006 0Z" />
  </svg>
);

export function RouteSmartInput() {
  const query = useRoutesStore((s) => s.query);
  const setQuery = useRoutesStore((s) => s.setQuery);
  const syncFiltersWithQuery = useRoutesStore((s) => s.syncFiltersWithQuery);
  const generateRoute = useRoutesStore((s) => s.generateRoute);
  const fetchSuggestions = useRoutesStore((s) => s.fetchSuggestions);
  const suggestions = useRoutesStore((s) => s.suggestions);
  const detectedEntities = useRoutesStore((s) => s.detectedEntities);
  const activeFilters = useRoutesStore((s) => s.activeFilters);
  const addFilter = useRoutesStore((s) => s.addFilter);
  const clearSuggestions = useRoutesStore((s) => s.clearSuggestions);
  const generating = useRoutesStore((s) => s.generating);

  const handleQueryChange = useCallback(
    (value: string) => {
      setQuery(value);
      syncFiltersWithQuery(value);
    },
    [setQuery, syncFiltersWithQuery],
  );

  const handleSubmit = useCallback(() => {
    generateRoute().catch(() => {
      // Error handled in store
    });
  }, [generateRoute]);

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
      onSubmit={handleSubmit}
      detectedEntities={detectedEntities}
      activeFilters={activeFilters}
      suggestions={suggestions}
      loading={generating}
      onEntitySelect={handleEntitySelect}
      onFetchSuggestions={fetchSuggestions}
      onClearSuggestions={clearSuggestions}
      placeholder="Describe la ruta que quieres explorar..."
      submitLabel="Generar ruta"
      icon={RouteIcon}
    />
  );
}
