"use client";

import { useSearchStore } from "@/store/search";
import { FilterChipsBase } from "@/components/shared/FilterChips";

export function FilterChips() {
  const activeFilters = useSearchStore((s) => s.activeFilters);
  const removeFilter = useSearchStore((s) => s.removeFilter);
  const clearFilters = useSearchStore((s) => s.clearFilters);

  return (
    <FilterChipsBase
      activeFilters={activeFilters}
      onRemoveFilter={removeFilter}
      onClearAll={clearFilters}
    />
  );
}
