"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import type { DetectedEntity } from "@/lib/api";
import type { ActiveFilter } from "@/lib/filterUtils";

// ── Shared constants ─────────────────────────────────────────────────────────

export const HERITAGE_TYPE_LABELS: Record<string, string> = {
  patrimonio_inmueble: "Patrimonio Inmueble",
  patrimonio_mueble: "Patrimonio Mueble",
  patrimonio_inmaterial: "Patrimonio Inmaterial",
  paisaje_cultural: "Paisaje Cultural",
};

export const TYPE_LABELS: Record<string, string> = {
  province: "Provincia",
  municipality: "Municipio",
  heritage_type: "Tipo",
};

export const TOOLTIP_COLORS: Record<string, string> = {
  province: "bg-blue-100 text-blue-800 hover:bg-blue-200",
  municipality: "bg-emerald-100 text-emerald-800 hover:bg-emerald-200",
  heritage_type: "bg-green-100 text-green-800 hover:bg-green-200",
};

// Raw color values for gradient construction
export const ACTIVE_COLOR: Record<string, string> = {
  province: "rgb(191 219 254)",       // blue-200
  municipality: "rgb(167 243 208)",   // emerald-200
  heritage_type: "rgb(187 247 208)",  // green-200
};

// Tailwind classes for single-entity active highlights
export const ACTIVE_BG: Record<string, string> = {
  province: "bg-blue-200/80",
  municipality: "bg-emerald-200/80",
  heritage_type: "bg-green-200/80",
};

// Neutral highlight for fully-pending entities
export const PENDING_BG = "bg-stone-300/50";

// ── Shared types ─────────────────────────────────────────────────────────────

export interface EntityInfo {
  entityType: string;
  value: string;
  displayLabel: string;
  matchedText: string;
}

export type { ActiveFilter } from "@/lib/filterUtils";

export interface Segment {
  kind: "text" | "potential" | "active";
  text: string;
  entities: EntityInfo[];
  activeEntities: EntityInfo[];
}

interface TooltipState {
  entities: EntityInfo[];
  x: number;
  y: number;
}

interface MatchInfo {
  start: number;
  end: number;
  entity: EntityInfo;
  isActive: boolean;
}

// ── Props ────────────────────────────────────────────────────────────────────

export interface SmartInputProps {
  query: string;
  onQueryChange: (value: string) => void;
  onSubmit: () => void;
  detectedEntities: DetectedEntity[];
  activeFilters: ActiveFilter[];
  loading: boolean;
  onEntitySelect: (entity: EntityInfo) => void;
  onFetchSuggestions: (query: string) => void;
  onClearSuggestions: () => void;
  placeholder?: string;
  /** Icon rendered in the input left side */
  icon?: React.ReactNode;
  /** Content rendered inside the input on the right (e.g. stop counter) */
  rightContent?: React.ReactNode;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

/**
 * Get highlight style for a segment.
 *
 * - No active entities -> neutral gray (Tailwind class)
 * - One active entity type -> solid color (Tailwind class)
 * - Multiple active entity types -> diagonal gradient (inline style)
 * - Mixed (some active, some pending) -> color of the active ones
 */
export function getHighlightStyle(seg: Segment): { className: string; style?: React.CSSProperties } {
  if (seg.activeEntities.length === 0) {
    return { className: PENDING_BG };
  }

  // Collect unique active entity types
  const uniqueTypes = [...new Set(seg.activeEntities.map((e) => e.entityType))];

  if (uniqueTypes.length === 1) {
    return { className: ACTIVE_BG[uniqueTypes[0]] ?? ACTIVE_BG.province };
  }

  // Multiple types -> diagonal gradient
  const colors = uniqueTypes.map((t) => ACTIVE_COLOR[t] ?? ACTIVE_COLOR.province);
  const stops = colors.map((c, idx) => {
    const from = (idx / colors.length) * 100;
    const to = ((idx + 1) / colors.length) * 100;
    return `${c} ${from}%, ${c} ${to}%`;
  });
  return {
    className: "",
    style: { background: `linear-gradient(135deg, ${stops.join(", ")})` },
  };
}

// ── Segment builder ─────────────────────────────────────────────────────────

export function buildSegments(
  query: string,
  detectedEntities: Array<{
    entity_type: string;
    value: string;
    display_label: string;
    matched_text: string;
  }>,
  activeFilters: ActiveFilter[],
): Segment[] {
  if (!query || detectedEntities.length === 0) {
    return [{ kind: "text", text: query, entities: [], activeEntities: [] }];
  }

  const matches: MatchInfo[] = [];
  for (const det of detectedEntities) {
    if (!det.matched_text) continue;
    const escaped = det.matched_text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const regex = new RegExp(escaped, "gi");
    let m: RegExpExecArray | null;
    while ((m = regex.exec(query)) !== null) {
      const isActive = activeFilters.some(
        (f) => f.type === (det.entity_type as ActiveFilter["type"]) && f.value === det.value,
      );
      matches.push({
        start: m.index,
        end: m.index + m[0].length,
        entity: {
          entityType: det.entity_type,
          value: det.value,
          displayLabel: det.display_label,
          matchedText: det.matched_text,
        },
        isActive,
      });
    }
  }

  if (matches.length === 0) {
    return [{ kind: "text", text: query, entities: [], activeEntities: [] }];
  }

  // Group matches at the same text position
  const spanMap = new Map<string, MatchInfo[]>();
  for (const m of matches) {
    const key = `${m.start}-${m.end}`;
    if (!spanMap.has(key)) spanMap.set(key, []);
    spanMap.get(key)!.push(m);
  }

  interface MergedSpan {
    start: number;
    end: number;
    entities: EntityInfo[];
    activeEntities: EntityInfo[];
  }

  const spans: MergedSpan[] = [];
  for (const [, group] of spanMap) {
    const first = group[0];
    spans.push({
      start: first.start,
      end: first.end,
      entities: group.map((m) => m.entity),
      activeEntities: group.filter((m) => m.isActive).map((m) => m.entity),
    });
  }

  spans.sort((a, b) => a.start - b.start || b.end - a.end);

  // Remove overlapping spans
  const filtered: MergedSpan[] = [];
  let lastEnd = 0;
  for (const s of spans) {
    if (s.start >= lastEnd) {
      filtered.push(s);
      lastEnd = s.end;
    }
  }

  const segments: Segment[] = [];
  let pos = 0;
  for (const s of filtered) {
    if (s.start > pos) {
      segments.push({ kind: "text", text: query.slice(pos, s.start), entities: [], activeEntities: [] });
    }
    const allActive = s.entities.length > 0 && s.activeEntities.length === s.entities.length;
    segments.push({
      kind: allActive ? "active" : "potential",
      text: query.slice(s.start, s.end),
      entities: s.entities,
      activeEntities: s.activeEntities,
    });
    pos = s.end;
  }
  if (pos < query.length) {
    segments.push({ kind: "text", text: query.slice(pos), entities: [], activeEntities: [] });
  }

  return segments;
}

// ── Default icons ────────────────────────────────────────────────────────────

const SearchIcon = (
  <svg
    className="w-5 h-5 text-stone-400"
    fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor"
  >
    <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
  </svg>
);

// ── Component ────────────────────────────────────────────────────────────────

export function SmartInput({
  query,
  onQueryChange,
  onSubmit,
  detectedEntities,
  activeFilters,
  loading,
  onEntitySelect,
  onFetchSuggestions,
  onClearSuggestions,
  placeholder = "Buscar en el patrimonio historico andaluz...",
  icon,
  rightContent,
}: SmartInputProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const tooltipHideRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const backdropRef = useRef<HTMLDivElement>(null);

  const resolvedIcon = icon ?? SearchIcon;

  const scheduleHideTooltip = useCallback(() => {
    tooltipHideRef.current = setTimeout(() => setTooltip(null), 200);
  }, []);

  const cancelHideTooltip = useCallback(() => {
    if (tooltipHideRef.current) {
      clearTimeout(tooltipHideRef.current);
      tooltipHideRef.current = null;
    }
  }, []);

  // Sync scroll between input and backdrop
  useEffect(() => {
    const input = inputRef.current;
    const backdrop = backdropRef.current;
    if (!input || !backdrop) return;
    const onScroll = () => {
      backdrop.scrollLeft = input.scrollLeft;
    };
    input.addEventListener("scroll", onScroll);
    return () => input.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setTooltip(null);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleChange = useCallback(
    (value: string) => {
      onQueryChange(value);
      setTooltip(null);
      if (debounceRef.current) clearTimeout(debounceRef.current);
      if (value.trim().length >= 2) {
        debounceRef.current = setTimeout(() => {
          onFetchSuggestions(value);
        }, 300);
      } else {
        onClearSuggestions();
      }
    },
    [onQueryChange, onFetchSuggestions, onClearSuggestions],
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    setTooltip(null);
    onClearSuggestions();
    onSubmit();
  };

  const handleEntitySelect = (entity: EntityInfo) => {
    onEntitySelect(entity);
    setTooltip((prev) => {
      if (!prev) return null;
      const remaining = prev.entities.filter(
        (e) => !(e.entityType === entity.entityType && e.value === entity.value),
      );
      return remaining.length > 0 ? { ...prev, entities: remaining } : null;
    });
    inputRef.current?.focus();
  };

  const handleEntityHover = (e: React.MouseEvent, entities: EntityInfo[]) => {
    const pending = entities.filter(
      (ent) => !activeFilters.some(
        (f) => f.type === (ent.entityType as ActiveFilter["type"]) && f.value === ent.value,
      ),
    );
    if (pending.length === 0) return;

    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const containerRect = containerRef.current?.getBoundingClientRect();
    if (!containerRect) return;
    setTooltip({
      entities: pending,
      x: rect.left - containerRect.left + rect.width / 2,
      y: rect.bottom - containerRect.top + 6,
    });
  };

  const segments = buildSegments(query, detectedEntities, activeFilters);
  const hasEntities = segments.some((s) => s.kind !== "text");

  // Shared text styles — must be identical between input and backdrop
  const textStyle: React.CSSProperties = {
    fontFamily: 'ui-sans-serif, system-ui, sans-serif, "Apple Color Emoji", "Segoe UI Emoji"',
    fontSize: "0.875rem",
    lineHeight: "1.25rem",
    fontWeight: 400,
    letterSpacing: "normal",
  };

  return (
    <div ref={containerRef} className="relative">
      <form onSubmit={handleSubmit}>
        <div className="relative">
          {/* Left icon */}
          <div className="absolute left-4 top-1/2 -translate-y-1/2 pointer-events-none z-10">
            {resolvedIcon}
          </div>

          {/* Backdrop overlay — on top, pointer-events-none except on entity spans */}
          <div
            ref={backdropRef}
            aria-hidden="true"
            className={`absolute inset-0 z-[2] pl-12 ${rightContent ? "pr-48" : "pr-12"} rounded-2xl overflow-hidden whitespace-pre pointer-events-none flex items-center`}
            style={textStyle}
          >
            {hasEntities
              ? segments.map((seg, i) => {
                  if (seg.kind === "text") {
                    return <span key={i} className="text-stone-800">{seg.text}</span>;
                  }

                  const hasPending = seg.activeEntities.length < seg.entities.length;
                  const highlight = getHighlightStyle(seg);

                  return (
                    <span
                      key={i}
                      className={`rounded py-0.5 px-[2px] -mx-[2px] text-stone-800 ${highlight.className} ${hasPending ? "cursor-pointer pointer-events-auto" : ""}`}
                      style={highlight.style}
                      onMouseEnter={hasPending ? (e) => { cancelHideTooltip(); handleEntityHover(e, seg.entities); } : undefined}
                      onMouseLeave={hasPending ? () => scheduleHideTooltip() : undefined}
                    >
                      {seg.text}
                    </span>
                  );
                })
              : null}
          </div>

          {/* Actual input — below backdrop, receives keyboard & cursor events */}
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => handleChange(e.target.value)}
            placeholder={placeholder}
            className={`w-full border border-stone-200 bg-white pl-12 ${rightContent ? "pr-48" : "pr-12"} py-4 rounded-2xl placeholder:text-stone-400 focus:border-green-500 focus:ring-2 focus:ring-green-100 outline-none shadow-sm transition-all relative`}
            style={{
              ...textStyle,
              background: hasEntities ? "transparent" : undefined,
              color: hasEntities ? "transparent" : undefined,
              caretColor: "black",
              WebkitTextFillColor: hasEntities ? "transparent" : undefined,
            }}
          />

          {/* Right zone: optional content + submit button */}
          <div className="absolute right-3 top-1/2 -translate-y-1/2 z-10 flex items-center gap-2">
            {rightContent}
            <button
              type="submit"
              disabled={!query.trim() || loading}
              className="h-8 w-8 shrink-0 flex items-center justify-center rounded-lg bg-green-600 text-white transition-all hover:bg-green-700 disabled:opacity-40 disabled:cursor-not-allowed"
              aria-label="Buscar"
            >
              {loading ? (
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                </svg>
              )}
            </button>
          </div>
        </div>
      </form>

      {/* Tooltip — shows pending entities for the hovered span */}
      {tooltip && (
        <div
          className="absolute z-50 -translate-x-1/2 bg-white border border-stone-200 rounded-lg shadow-lg p-2 flex flex-col gap-1.5 text-xs whitespace-nowrap"
          style={{ left: tooltip.x, top: tooltip.y }}
          onMouseEnter={() => cancelHideTooltip()}
          onMouseLeave={() => scheduleHideTooltip()}
        >
          {tooltip.entities.map((ent, i) => {
            const colorClass = TOOLTIP_COLORS[ent.entityType] ?? "bg-stone-100 text-stone-800 hover:bg-stone-200";
            return (
              <button
                key={`${ent.entityType}-${ent.value}-${i}`}
                onClick={() => handleEntitySelect(ent)}
                className={`flex items-center gap-2 px-2.5 py-1.5 rounded-md transition-colors ${colorClass}`}
              >
                <span className="text-stone-500">{TYPE_LABELS[ent.entityType]}:</span>
                <span className="font-medium">{ent.value}</span>
                <span className="opacity-50 ml-1">+ Filtrar</span>
              </button>
            );
          })}
        </div>
      )}

    </div>
  );
}
