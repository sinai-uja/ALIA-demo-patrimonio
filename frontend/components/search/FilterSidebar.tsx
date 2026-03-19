"use client";

import { useSearchStore } from "@/store/search";
import { FilterSidebarBase } from "@/components/shared/FilterSidebar";

export function FilterSidebar() {
  const activeFilters = useSearchStore((s) => s.activeFilters);
  const filterValues = useSearchStore((s) => s.filterValues);
  const addFilter = useSearchStore((s) => s.addFilter);
  const removeFilter = useSearchStore((s) => s.removeFilter);
  const clearFilters = useSearchStore((s) => s.clearFilters);

  return (
    <FilterSidebarBase
      filterValues={filterValues}
      activeFilters={activeFilters}
      onAddFilter={addFilter}
      onRemoveFilter={removeFilter}
      onClearAll={clearFilters}
    />
  );
}
