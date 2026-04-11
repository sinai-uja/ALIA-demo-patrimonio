import { create } from "zustand";
import {
  routes as routesApi,
  heritage as heritageApi,
  type VirtualRoute,
  type RouteStop,
  type HeritageAsset,
  type SuggestionResponse,
  type FilterValues,
  type DetectedEntity,
} from "@/lib/api";
import { type ActiveFilter, collectFilters } from "@/lib/filterUtils";
import { minDelay } from "@/lib/minDelay";

/** Strip diacritics and lowercase for accent-insensitive matching. */
function normalize(s: string): string {
  return s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
}

interface RoutesState {
  // Smart input
  query: string;
  activeFilters: ActiveFilter[];
  detectedEntities: DetectedEntity[];
  suggestions: SuggestionResponse | null;
  filterValues: FilterValues | null;
  numStops: number;
  suggestionsLoading: boolean;

  // Generation
  generating: boolean;
  generatedRoute: VirtualRoute | null;

  // Streaming state
  streamingSteps: { step: string; status: string; detail?: string }[];
  streamingStops: RouteStop[];
  streamingTitle: string | null;
  streamingIntroduction: string | null;
  streamingConclusion: string | null;
  streamingNarratives: Record<number, string>;
  streamingError: string | null;

  // Route list
  routes: VirtualRoute[];
  activeRoute: VirtualRoute | null;
  loading: boolean;
  routesPage: number;
  routesPageSize: number;
  routesFilter: string;

  // Stop detail panel
  selectedStopAssetId: string | null;
  selectedAsset: HeritageAsset | null;
  detailLoading: boolean;

  // Edit mode
  editing: boolean;
  editLoading: boolean;

  // Actions
  setQuery: (q: string) => void;
  setNumStops: (n: number) => void;
  syncFiltersWithQuery: (q: string) => void;
  fetchSuggestions: (q: string) => Promise<void>;
  loadFilterValues: (provinces?: string[]) => Promise<void>;
  addFilter: (filter: ActiveFilter) => void;
  addFilters: (filters: ActiveFilter[]) => void;
  removeFilter: (filter: ActiveFilter) => void;
  clearFilters: () => void;
  clearSuggestions: () => void;
  setRoutesFilter: (q: string) => void;
  filteredRoutes: () => VirtualRoute[];
  routesTotalPages: () => number;
  paginatedRoutes: () => VirtualRoute[];
  goToRoutesPage: (page: number) => void;
  generateRoute: () => Promise<VirtualRoute>;
  loadRoutes: () => Promise<void>;
  selectRoute: (id: string) => Promise<void>;
  deleteRoute: (id: string) => Promise<void>;
  openStopDetail: (heritageAssetId: string) => Promise<void>;
  closeStopDetail: () => void;
  setEditMode: (editing: boolean) => void;
  removeStop: (routeId: string, stopOrder: number) => Promise<void>;
  addStop: (routeId: string, documentId: string, position?: number) => Promise<void>;
}

let _generateController: AbortController | null = null;

export const useRoutesStore = create<RoutesState>((set, get) => ({
  // Smart input
  query: "",
  activeFilters: [],
  detectedEntities: [],
  suggestions: null,
  filterValues: null,
  numStops: 5,
  suggestionsLoading: false,

  // Generation
  generating: false,
  generatedRoute: null,

  // Streaming state
  streamingSteps: [],
  streamingStops: [],
  streamingTitle: null,
  streamingIntroduction: null,
  streamingConclusion: null,
  streamingNarratives: {},
  streamingError: null,

  // Route list
  routes: [],
  activeRoute: null,
  loading: false,
  routesPage: 1,
  routesPageSize: 6,
  routesFilter: "",

  // Stop detail panel
  selectedStopAssetId: null,
  selectedAsset: null,
  detailLoading: false,

  // Edit mode
  editing: false,
  editLoading: false,

  setQuery: (q) => set({ query: q }),

  setNumStops: (n) => set({ numStops: n }),

  syncFiltersWithQuery: (q: string) => {
    const { activeFilters } = get();
    if (activeFilters.length === 0) return;
    const lower = q.toLowerCase();
    const remaining = activeFilters.filter((f) => {
      if (!f.matchedText) return true;
      // Heritage type filters stay regardless of query text
      if (f.type === "heritage_type") return true;
      return lower.includes(f.matchedText.toLowerCase());
    });
    if (remaining.length !== activeFilters.length) {
      set({ activeFilters: remaining });
    }
  },

  fetchSuggestions: async (q) => {
    if (!q.trim() || q.trim().length < 2) {
      set({ suggestions: null, detectedEntities: [] });
      return;
    }
    set({ suggestionsLoading: true });
    try {
      const res = await routesApi.suggestions(q.trim());
      set({ suggestions: res, detectedEntities: res.detected_entities });
    } catch {
      set({ suggestions: null });
    } finally {
      set({ suggestionsLoading: false });
    }
  },

  loadFilterValues: async (provinces) => {
    try {
      const values = await routesApi.filters(provinces);
      set({ filterValues: values });
    } catch {
      /* ignore */
    }
  },

  addFilter: (filter) => {
    const { activeFilters } = get();
    const exists = activeFilters.some(
      (f) => f.type === filter.type && f.value === filter.value
    );
    if (exists) return;
    const updated = [...activeFilters, filter];
    set({ activeFilters: updated });
    if (filter.type === "province") {
      const provinces = updated.filter((f) => f.type === "province").map((f) => f.value);
      get().loadFilterValues(provinces);
    }
  },

  addFilters: (filters) => {
    const { activeFilters } = get();
    const newFilters = filters.filter(
      (f) => !activeFilters.some((a) => a.type === f.type && a.value === f.value)
    );
    if (newFilters.length === 0) return;
    const updated = [...activeFilters, ...newFilters];
    set({ activeFilters: updated });
    const hasProvince = newFilters.some((f) => f.type === "province");
    if (hasProvince) {
      const provinces = updated.filter((f) => f.type === "province").map((f) => f.value);
      get().loadFilterValues(provinces);
    }
  },

  removeFilter: (filter) => {
    const { activeFilters } = get();
    const updated = activeFilters.filter(
      (f) => !(f.type === filter.type && f.value === filter.value)
    );
    set({ activeFilters: updated });
    if (filter.type === "province") {
      const provinces = updated.filter((f) => f.type === "province").map((f) => f.value);
      get().loadFilterValues(provinces.length ? provinces : undefined);
    }
  },

  clearFilters: () => {
    set({ activeFilters: [] });
    get().loadFilterValues();
  },

  clearSuggestions: () => set({ suggestions: null }),

  setRoutesFilter: (q) => set({ routesFilter: q, routesPage: 1 }),

  filteredRoutes: () => {
    const { routes, routesFilter } = get();
    if (!routesFilter.trim()) return routes;
    const norm = normalize(routesFilter);
    return routes.filter((r) => normalize(r.title).includes(norm));
  },

  routesTotalPages: () => {
    const filtered = get().filteredRoutes();
    return Math.max(1, Math.ceil(filtered.length / get().routesPageSize));
  },

  paginatedRoutes: () => {
    const { routesPage, routesPageSize } = get();
    const filtered = get().filteredRoutes();
    const start = (routesPage - 1) * routesPageSize;
    return filtered.slice(start, start + routesPageSize);
  },

  goToRoutesPage: (page) => {
    const totalPages = get().routesTotalPages();
    set({ routesPage: Math.max(1, Math.min(page, totalPages)) });
  },

  generateRoute: async () => {
    const { query, activeFilters, numStops, generating } = get();
    if (!query.trim()) throw new Error("La consulta no puede estar vacia");

    // Skip if a generation is already in progress (prevents same-tick duplicates)
    if (generating) return get().generatedRoute as VirtualRoute;

    // Abort any in-flight generation to prevent stale responses
    _generateController?.abort();
    const controller = new AbortController();
    _generateController = controller;

    // Reset streaming state
    set({
      generating: true,
      generatedRoute: null,
      streamingSteps: [],
      streamingStops: [],
      streamingTitle: null,
      streamingIntroduction: null,
      streamingConclusion: null,
      streamingNarratives: {},
      streamingError: null,
    });

    const filters = collectFilters(activeFilters);
    const params = {
      query: query.trim(),
      num_stops: numStops,
      ...filters,
    };

    try {
      await routesApi.generateStream(params, controller.signal, (ev) => {
        if (controller.signal.aborted) return;

        switch (ev.event) {
          case "step": {
            const { step, status, ...rest } = ev.data as { step: string; status: string; [k: string]: unknown };
            set((s) => {
              const existing = s.streamingSteps.findIndex((ss) => ss.step === step);
              const detail = rest.extracted_query
                ? String(rest.extracted_query)
                : rest.chunks
                  ? `${rest.chunks} fragmentos`
                  : rest.count
                    ? `${rest.count} resultados`
                    : undefined;
              const entry = { step, status, detail };
              if (existing >= 0) {
                const updated = [...s.streamingSteps];
                updated[existing] = entry;
                return { streamingSteps: updated };
              }
              return { streamingSteps: [...s.streamingSteps, entry] };
            });
            break;
          }

          case "stop": {
            const stop = ev.data as unknown as RouteStop;
            set((s) => ({
              streamingStops: [...s.streamingStops, stop],
            }));
            break;
          }

          case "narrative": {
            const { order, type, text, title } = ev.data as {
              order: number;
              type: string;
              text?: string;
              title?: string;
            };
            if (type === "introduction") {
              set({
                streamingTitle: title ? String(title) : null,
                streamingIntroduction: text ? String(text) : null,
              });
            } else if (type === "stop") {
              set((s) => ({
                streamingNarratives: { ...s.streamingNarratives, [order]: String(text ?? "") },
              }));
            } else if (type === "conclusion") {
              set({ streamingConclusion: text ? String(text) : null });
            }
            break;
          }

          case "complete": {
            const { route_id } = ev.data as { route_id: string };
            // Fetch the full route from the server
            routesApi.get(route_id).then((fullRoute) => {
              set((s) => ({
                generatedRoute: fullRoute,
                activeRoute: fullRoute,
                routes: [fullRoute, ...s.routes],
                generating: false,
                // Clear streaming state
                streamingSteps: [],
                streamingStops: [],
                streamingTitle: null,
                streamingIntroduction: null,
                streamingConclusion: null,
                streamingNarratives: {},
              }));
            }).catch(() => {
              // If fetching full route fails, still stop generating
              set({ generating: false, streamingError: "Error al cargar la ruta completa" });
            });
            break;
          }

          case "error": {
            const { message } = ev.data as { message: string };
            set({
              streamingError: message || "Error durante la generacion",
              generating: false,
            });
            break;
          }
        }
      });

      // Stream ended — if no complete event was fired, stop generating
      // (complete event handler sets generating: false asynchronously)
      const state = get();
      if (state.generating && !state.generatedRoute) {
        // Stream ended without complete event — possibly an error
        set({ generating: false });
      }

      return get().generatedRoute as VirtualRoute;
    } catch (err) {
      if (controller.signal.aborted) {
        set({
          generating: false,
          streamingSteps: [],
          streamingStops: [],
          streamingTitle: null,
          streamingIntroduction: null,
          streamingConclusion: null,
          streamingNarratives: {},
          streamingError: null,
        });
        throw new DOMException("Aborted", "AbortError");
      }
      set({
        generating: false,
        streamingError: err instanceof Error ? err.message : "Error desconocido",
      });
      throw err;
    }
  },

  loadRoutes: async () => {
    set({ loading: true });
    try {
      const routes = await minDelay(routesApi.list());
      set({ routes });
    } finally {
      set({ loading: false });
    }
  },

  selectRoute: async (id) => {
    set({ loading: true });
    try {
      const route = await minDelay(routesApi.get(id));
      set({ activeRoute: route });
    } finally {
      set({ loading: false });
    }
  },

  deleteRoute: async (id) => {
    await routesApi.delete(id);
    set((s) => ({
      routes: s.routes.filter((r) => r.id !== id),
      generatedRoute: s.generatedRoute?.id === id ? null : s.generatedRoute,
      activeRoute: s.activeRoute?.id === id ? null : s.activeRoute,
    }));
  },

  openStopDetail: async (heritageAssetId) => {
    set({ selectedStopAssetId: heritageAssetId, detailLoading: true, selectedAsset: null });
    try {
      const asset = await minDelay(heritageApi.get(heritageAssetId));
      set({ selectedAsset: asset, detailLoading: false });
    } catch {
      set({ selectedStopAssetId: null, detailLoading: false });
    }
  },

  closeStopDetail: () => {
    set({ selectedStopAssetId: null, selectedAsset: null, detailLoading: false });
  },

  setEditMode: (editing) => set({ editing }),

  removeStop: async (routeId, stopOrder) => {
    set({ editLoading: true });
    try {
      const updated = await routesApi.removeStop(routeId, stopOrder);
      set((s) => ({
        activeRoute: updated,
        routes: s.routes.map((r) => (r.id === routeId ? updated : r)),
      }));
    } finally {
      set({ editLoading: false });
    }
  },

  addStop: async (routeId, documentId, position) => {
    set({ editLoading: true });
    try {
      const updated = await routesApi.addStop(routeId, documentId, position);
      set((s) => ({
        activeRoute: updated,
        routes: s.routes.map((r) => (r.id === routeId ? updated : r)),
      }));
    } finally {
      set({ editLoading: false });
    }
  },
}));
