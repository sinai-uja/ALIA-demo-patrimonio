"use client";

import { useEffect, useRef, useState } from "react";
import { useSearchStore, type ActiveFilter } from "@/store/search";

const HERITAGE_TYPE_LABELS: Record<string, string> = {
  patrimonio_inmueble: "Patrimonio Inmueble",
  patrimonio_mueble: "Patrimonio Mueble",
  patrimonio_inmaterial: "Patrimonio Inmaterial",
  paisaje_cultural: "Paisaje Cultural",
};

const ENTITY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  province: { bg: "bg-blue-100", text: "text-blue-700", border: "border-blue-300" },
  municipality: { bg: "bg-emerald-100", text: "text-emerald-700", border: "border-emerald-300" },
  heritage_type: { bg: "bg-amber-100", text: "text-amber-700", border: "border-amber-300" },
};

const TYPE_LABELS: Record<string, string> = {
  province: "Provincia",
  municipality: "Municipio",
  heritage_type: "Tipo",
};

export function SearchInput() {
  const query = useSearchStore((s) => s.query);
  const setQuery = useSearchStore((s) => s.setQuery);
  const performSearch = useSearchStore((s) => s.performSearch);
  const fetchSuggestions = useSearchStore((s) => s.fetchSuggestions);
  const suggestions = useSearchStore((s) => s.suggestions);
  const activeFilters = useSearchStore((s) => s.activeFilters);
  const addFilter = useSearchStore((s) => s.addFilter);
  const clearSuggestions = useSearchStore((s) => s.clearSuggestions);
  const loading = useSearchStore((s) => s.loading);

  const [showDropdown, setShowDropdown] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleChange = (value: string) => {
    setQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    if (value.trim().length >= 2) {
      setShowDropdown(true);
      debounceRef.current = setTimeout(() => {
        fetchSuggestions(value);
      }, 300);
    } else {
      setShowDropdown(false);
      clearSuggestions();
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setShowDropdown(false);
    clearSuggestions();
    performSearch();
  };

  const handleSearchSuggestionClick = () => {
    setShowDropdown(false);
    clearSuggestions();
    performSearch();
  };

  const handleEntityClick = (entity: {
    entity_type: string;
    value: string;
    display_label: string;
    matched_text: string;
  }) => {
    const typeMap: Record<string, "province" | "municipality" | "heritage_type"> = {
      province: "province",
      municipality: "municipality",
      heritage_type: "heritage_type",
    };
    const filterType = typeMap[entity.entity_type];
    if (!filterType) return;

    let label = entity.value;
    if (filterType === "heritage_type") {
      label = HERITAGE_TYPE_LABELS[entity.value] ?? entity.value;
    }

    addFilter({ type: filterType, value: entity.value, label });
    // Don't remove text from input — keep it for context
    setShowDropdown(false);
  };

  // Check if a detected entity is already an active filter
  const isAlreadyFiltered = (entityType: string, value: string): boolean => {
    const typeMap: Record<string, ActiveFilter["type"]> = {
      province: "province",
      municipality: "municipality",
      heritage_type: "heritage_type",
    };
    const ft = typeMap[entityType];
    return activeFilters.some((f) => f.type === ft && f.value === value);
  };

  const entities = (suggestions?.detected_entities ?? []).filter(
    (e) => !isAlreadyFiltered(e.entity_type, e.value)
  );

  // Build highlighted text preview with clickable entity segments
  const highlightSegments = buildHighlightedText(
    query,
    suggestions?.detected_entities ?? [],
    activeFilters,
  );

  const showHighlights =
    query.trim().length >= 2 &&
    !showDropdown &&
    highlightSegments.some((s) => s.type !== "text");

  return (
    <div ref={containerRef} className="relative">
      <form onSubmit={handleSubmit}>
        <div className="relative">
          <svg
            className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-stone-400"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={1.5}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
            />
          </svg>
          <input
            type="text"
            value={query}
            onChange={(e) => handleChange(e.target.value)}
            onFocus={() => {
              if (query.trim().length >= 2) setShowDropdown(true);
            }}
            placeholder="Buscar en el patrimonio historico andaluz..."
            className="w-full rounded-2xl border border-stone-200 bg-white pl-12 pr-4 py-4 text-sm text-stone-800 placeholder:text-stone-400 focus:border-amber-400 focus:ring-2 focus:ring-amber-100 outline-none shadow-sm transition-all"
          />
          {loading && (
            <svg
              className="absolute right-4 top-1/2 -translate-y-1/2 w-5 h-5 animate-spin text-amber-500"
              fill="none"
              viewBox="0 0 24 24"
            >
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
          )}
        </div>
      </form>

      {/* Inline highlight preview — shows detected entities in the text */}
      {showHighlights && (
        <div className="mt-2 px-2 flex flex-wrap items-center gap-0.5 text-sm text-stone-600 leading-relaxed">
          {highlightSegments.map((seg, i) => {
            if (seg.type === "text") {
              return <span key={i}>{seg.text}</span>;
            }
            const colors = ENTITY_COLORS[seg.entityType!] ?? ENTITY_COLORS.province;
            const typeLabel = TYPE_LABELS[seg.entityType!] ?? "";
            return (
              <button
                key={i}
                onClick={() =>
                  handleEntityClick({
                    entity_type: seg.entityType!,
                    value: seg.entityValue!,
                    display_label: seg.displayLabel!,
                    matched_text: seg.text,
                  })
                }
                className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-xs font-medium cursor-pointer hover:shadow-sm transition-all ${colors.bg} ${colors.text} ${colors.border}`}
                title={`Filtrar por ${typeLabel}: ${seg.entityValue}`}
              >
                {seg.text}
                <svg className="w-3 h-3 opacity-50" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
                </svg>
              </button>
            );
          })}
        </div>
      )}

      {/* Dropdown suggestions */}
      {showDropdown && query.trim().length >= 2 && (
        <div className="absolute z-50 mt-1.5 w-full rounded-xl border border-stone-200 bg-white shadow-lg overflow-hidden">
          <button
            onClick={handleSearchSuggestionClick}
            className="w-full text-left px-4 py-3 text-sm hover:bg-stone-50 transition-colors flex items-center gap-3 border-b border-stone-100"
          >
            <svg className="w-4 h-4 text-amber-500 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
            </svg>
            <span>
              Buscar <span className="font-semibold text-stone-800">&ldquo;{query.trim()}&rdquo;</span>{" "}
              <span className="text-stone-400">por similaridad</span>
            </span>
          </button>

          {entities.map((entity, i) => {
            const colors = ENTITY_COLORS[entity.entity_type] ?? ENTITY_COLORS.province;
            return (
              <button
                key={`${entity.entity_type}-${entity.value}-${i}`}
                onClick={() => handleEntityClick(entity)}
                className="w-full text-left px-4 py-2.5 text-sm hover:bg-stone-50 transition-colors flex items-center gap-3"
              >
                <svg className="w-4 h-4 text-stone-300 shrink-0" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 3c2.755 0 5.455.232 8.083.678.533.09.917.556.917 1.096v1.044a2.25 2.25 0 0 1-.659 1.591l-5.432 5.432a2.25 2.25 0 0 0-.659 1.591v2.927a2.25 2.25 0 0 1-1.244 2.013L9.75 21v-6.568a2.25 2.25 0 0 0-.659-1.591L3.659 7.409A2.25 2.25 0 0 1 3 5.818V4.774c0-.54.384-1.006.917-1.096A48.32 48.32 0 0 1 12 3Z" />
                </svg>
                <span className="flex items-center gap-2">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${colors.bg} ${colors.text}`}>
                    {entity.display_label}
                  </span>
                  <span className="text-xs text-stone-400">Filtrar</span>
                </span>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ── Highlight builder ──────────────────────────────────────────────────────────

interface HighlightSegment {
  type: "text" | "entity";
  text: string;
  entityType?: string;
  entityValue?: string;
  displayLabel?: string;
}

function buildHighlightedText(
  query: string,
  detectedEntities: Array<{
    entity_type: string;
    value: string;
    display_label: string;
    matched_text: string;
  }>,
  activeFilters: ActiveFilter[],
): HighlightSegment[] {
  if (!query || detectedEntities.length === 0) {
    return [{ type: "text", text: query }];
  }

  // Filter out entities that are already active filters
  const typeMap: Record<string, ActiveFilter["type"]> = {
    province: "province",
    municipality: "municipality",
    heritage_type: "heritage_type",
  };
  const available = detectedEntities.filter(
    (e) =>
      !activeFilters.some(
        (f) => f.type === typeMap[e.entity_type] && f.value === e.value
      )
  );

  if (available.length === 0) {
    return [{ type: "text", text: query }];
  }

  // Find all match positions in the query (case-insensitive)
  interface MatchInfo {
    start: number;
    end: number;
    entity: (typeof available)[0];
  }

  const matches: MatchInfo[] = [];
  for (const entity of available) {
    if (!entity.matched_text) continue;
    const escaped = entity.matched_text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const regex = new RegExp(escaped, "gi");
    let match: RegExpExecArray | null;
    while ((match = regex.exec(query)) !== null) {
      matches.push({ start: match.index, end: match.index + match[0].length, entity });
    }
  }

  if (matches.length === 0) {
    return [{ type: "text", text: query }];
  }

  // Sort by start position, longest first for overlaps
  matches.sort((a, b) => a.start - b.start || b.end - a.end);

  // Remove overlapping matches (keep first/longest)
  const filtered: MatchInfo[] = [];
  let lastEnd = 0;
  for (const m of matches) {
    if (m.start >= lastEnd) {
      filtered.push(m);
      lastEnd = m.end;
    }
  }

  // Build segments
  const segments: HighlightSegment[] = [];
  let pos = 0;
  for (const m of filtered) {
    if (m.start > pos) {
      segments.push({ type: "text", text: query.slice(pos, m.start) });
    }
    segments.push({
      type: "entity",
      text: query.slice(m.start, m.end),
      entityType: m.entity.entity_type,
      entityValue: m.entity.value,
      displayLabel: m.entity.display_label,
    });
    pos = m.end;
  }
  if (pos < query.length) {
    segments.push({ type: "text", text: query.slice(pos) });
  }

  return segments;
}
