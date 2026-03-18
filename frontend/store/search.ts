import { create } from "zustand";
import {
  search as searchApi,
  type SearchResult,
  type SuggestionResponse,
  type FilterValues,
} from "@/lib/api";

export interface ActiveFilter {
  type: "province" | "municipality" | "heritage_type";
  value: string;
  label: string;
}

interface SearchState {
  query: string;
  results: SearchResult[];
  totalResults: number;
  activeFilters: ActiveFilter[];
  suggestions: SuggestionResponse | null;
  filterValues: FilterValues | null;
  loading: boolean;
  suggestionsLoading: boolean;
  hasSearched: boolean;

  setQuery: (q: string) => void;
  performSearch: () => Promise<void>;
  fetchSuggestions: (q: string) => Promise<void>;
  loadFilterValues: (province?: string) => Promise<void>;
  addFilter: (filter: ActiveFilter) => void;
  removeFilter: (filter: ActiveFilter) => void;
  clearFilters: () => void;
  clearSuggestions: () => void;
}

function collectFilters(filters: ActiveFilter[]) {
  const heritage: string[] = [];
  const provinces: string[] = [];
  const municipalities: string[] = [];
  for (const f of filters) {
    if (f.type === "heritage_type") heritage.push(f.value);
    if (f.type === "province") provinces.push(f.value);
    if (f.type === "municipality") municipalities.push(f.value);
  }
  return {
    heritage_type_filter: heritage.length ? heritage : null,
    province_filter: provinces.length ? provinces : null,
    municipality_filter: municipalities.length ? municipalities : null,
  };
}

export const useSearchStore = create<SearchState>((set, get) => ({
  query: "",
  results: [],
  totalResults: 0,
  activeFilters: [],
  suggestions: null,
  filterValues: null,
  loading: false,
  suggestionsLoading: false,
  hasSearched: false,

  setQuery: (q) => set({ query: q }),

  performSearch: async () => {
    const { query, activeFilters } = get();
    if (!query.trim()) return;

    set({ loading: true, hasSearched: true });
    try {
      const filters = collectFilters(activeFilters);
      const res = await searchApi.similarity({
        query: query.trim(),
        top_k: 20,
        ...filters,
      });
      set({ results: res.results, totalResults: res.total_results });
    } catch {
      set({ results: [], totalResults: 0 });
    } finally {
      set({ loading: false });
    }
  },

  fetchSuggestions: async (q) => {
    if (!q.trim() || q.trim().length < 2) {
      set({ suggestions: null });
      return;
    }
    set({ suggestionsLoading: true });
    try {
      const res = await searchApi.suggestions(q.trim());
      set({ suggestions: res });
    } catch {
      set({ suggestions: null });
    } finally {
      set({ suggestionsLoading: false });
    }
  },

  loadFilterValues: async (province) => {
    try {
      const values = await searchApi.filters(province);
      set({ filterValues: values });
    } catch {
      /* ignore */
    }
  },

  addFilter: (filter) => {
    const { activeFilters } = get();
    // Allow multiple of the same type (OR), but not duplicate value
    const exists = activeFilters.some(
      (f) => f.type === filter.type && f.value === filter.value
    );
    if (exists) return;
    const updated = [...activeFilters, filter];
    set({ activeFilters: updated, suggestions: null });
    // Auto-search if we have a query
    if (get().query.trim()) {
      get().performSearch();
    }
  },

  removeFilter: (filter) => {
    const { activeFilters } = get();
    const updated = activeFilters.filter(
      (f) => !(f.type === filter.type && f.value === filter.value)
    );
    set({ activeFilters: updated });
    if (get().query.trim()) {
      get().performSearch();
    }
  },

  clearFilters: () => {
    set({ activeFilters: [] });
    if (get().query.trim()) {
      get().performSearch();
    }
  },

  clearSuggestions: () => set({ suggestions: null }),
}));
