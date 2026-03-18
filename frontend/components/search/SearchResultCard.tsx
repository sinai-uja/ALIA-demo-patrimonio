"use client";

import type { SearchResult } from "@/lib/api";

const HERITAGE_LABELS: Record<string, string> = {
  patrimonio_inmueble: "Patrimonio Inmueble",
  patrimonio_mueble: "Patrimonio Mueble",
  patrimonio_inmaterial: "Patrimonio Inmaterial",
  paisaje_cultural: "Paisaje Cultural",
};

const HERITAGE_COLORS: Record<string, string> = {
  patrimonio_inmueble: "bg-amber-100 text-amber-800",
  patrimonio_mueble: "bg-violet-100 text-violet-800",
  patrimonio_inmaterial: "bg-emerald-100 text-emerald-800",
  paisaje_cultural: "bg-sky-100 text-sky-800",
};

function truncate(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen).trimEnd() + "...";
}

function scoreToPercent(score: number): number {
  // Score is cosine distance (0 = identical, 1 = orthogonal)
  // Convert to similarity percentage
  return Math.max(0, Math.round((1 - score) * 100));
}

export function SearchResultCard({ result, rank }: { result: SearchResult; rank: number }) {
  const similarity = scoreToPercent(result.score);
  const heritageLabel = HERITAGE_LABELS[result.heritage_type] ?? result.heritage_type;
  const heritageColor = HERITAGE_COLORS[result.heritage_type] ?? "bg-stone-100 text-stone-700";

  return (
    <div className="rounded-2xl border border-stone-200/60 bg-white p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs font-bold text-stone-300">#{rank}</span>
            <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${heritageColor}`}>
              {heritageLabel}
            </span>
          </div>
          <h3 className="font-semibold text-stone-900 text-sm leading-snug mb-1.5">
            {result.url ? (
              <a
                href={result.url}
                target="_blank"
                rel="noopener noreferrer"
                className="hover:text-amber-700 transition-colors"
              >
                {result.title}
              </a>
            ) : (
              result.title
            )}
          </h3>
          <div className="flex items-center gap-3 text-xs text-stone-400 mb-3">
            {result.province && (
              <span className="flex items-center gap-1">
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 0 1 15 0Z" />
                </svg>
                {result.province}
              </span>
            )}
            {result.municipality && (
              <span>{result.municipality}</span>
            )}
          </div>
          <p className="text-xs text-stone-500 leading-relaxed">
            {truncate(result.content, 250)}
          </p>
        </div>
        <div className="shrink-0 flex flex-col items-center gap-1">
          <div
            className="w-12 h-12 rounded-full flex items-center justify-center text-xs font-bold"
            style={{
              background: `conic-gradient(#f59e0b ${similarity}%, #f5f5f4 ${similarity}%)`,
            }}
          >
            <span className="w-9 h-9 rounded-full bg-white flex items-center justify-center text-stone-700">
              {similarity}%
            </span>
          </div>
          <span className="text-[10px] text-stone-400">similitud</span>
        </div>
      </div>
    </div>
  );
}
