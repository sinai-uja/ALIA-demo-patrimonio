"use client";

import { useRoutesStore } from "@/store/routes";

export function RoutesPagination() {
  const page = useRoutesStore((s) => s.routesPage);
  const totalPages = useRoutesStore((s) => s.routesTotalPages());
  const goToPage = useRoutesStore((s) => s.goToRoutesPage);

  if (totalPages <= 1) return null;

  const pages = new Set<number>();
  pages.add(1);
  pages.add(totalPages);
  for (let i = Math.max(1, page - 1); i <= Math.min(totalPages, page + 1); i++) {
    pages.add(i);
  }
  const sorted = [...pages].sort((a, b) => a - b);

  const items: (number | "ellipsis")[] = [];
  for (let i = 0; i < sorted.length; i++) {
    if (i > 0 && sorted[i] - sorted[i - 1] > 1) items.push("ellipsis");
    items.push(sorted[i]);
  }

  return (
    <nav className="flex items-center justify-center gap-1 pt-2 pb-2" aria-label="Paginacion">
      <button
        onClick={() => goToPage(page - 1)}
        disabled={page <= 1}
        className="px-2 py-1 rounded text-xs text-stone-500 hover:bg-stone-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        aria-label="Pagina anterior"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
        </svg>
      </button>
      {items.map((item, idx) =>
        item === "ellipsis" ? (
          <span key={`e-${idx}`} className="px-1 text-xs text-stone-300">...</span>
        ) : (
          <button
            key={item}
            onClick={() => goToPage(item)}
            className={`min-w-[2rem] px-2 py-1 rounded text-xs font-medium transition-colors ${
              item === page
                ? "bg-green-600 text-white"
                : "text-stone-500 hover:bg-stone-100"
            }`}
          >
            {item}
          </button>
        ),
      )}
      <button
        onClick={() => goToPage(page + 1)}
        disabled={page >= totalPages}
        className="px-2 py-1 rounded text-xs text-stone-500 hover:bg-stone-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
        aria-label="Pagina siguiente"
      >
        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
        </svg>
      </button>
    </nav>
  );
}
