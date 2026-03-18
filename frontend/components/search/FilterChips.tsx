"use client";

import { useSearchStore, type ActiveFilter } from "@/store/search";

const TYPE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  province: { bg: "bg-blue-50", text: "text-blue-700", border: "border-blue-200" },
  municipality: { bg: "bg-emerald-50", text: "text-emerald-700", border: "border-emerald-200" },
  heritage_type: { bg: "bg-amber-50", text: "text-amber-700", border: "border-amber-200" },
};

const TYPE_ICONS: Record<string, string> = {
  province: "Provincia",
  municipality: "Municipio",
  heritage_type: "Tipo",
};

export function FilterChips() {
  const activeFilters = useSearchStore((s) => s.activeFilters);
  const removeFilter = useSearchStore((s) => s.removeFilter);
  const clearFilters = useSearchStore((s) => s.clearFilters);

  if (activeFilters.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-xs text-stone-400 font-medium">Filtros activos:</span>
      {activeFilters.map((f: ActiveFilter) => {
        const colors = TYPE_COLORS[f.type] ?? TYPE_COLORS.province;
        return (
          <span
            key={`${f.type}-${f.value}`}
            className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium ${colors.bg} ${colors.text} ${colors.border}`}
          >
            <span className="opacity-60">{TYPE_ICONS[f.type]}:</span>
            {f.label}
            <button
              onClick={() => removeFilter(f)}
              className="ml-0.5 rounded-full p-0.5 hover:bg-black/5 transition-colors"
              aria-label={`Quitar filtro ${f.label}`}
            >
              <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
              </svg>
            </button>
          </span>
        );
      })}
      {activeFilters.length > 1 && (
        <button
          onClick={clearFilters}
          className="text-xs text-stone-400 hover:text-stone-600 transition-colors underline"
        >
          Limpiar todos
        </button>
      )}
    </div>
  );
}
