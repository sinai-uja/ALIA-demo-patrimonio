"use client";

import { useState } from "react";
import type { SearchResult } from "@/lib/api";
import { useSearchStore } from "@/store/search";

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

function scoreToPercent(score: number): number {
  return Math.max(0, Math.round((1 - score) * 100));
}

function truncate(text: string, maxLen: number): string {
  if (text.length <= maxLen) return text;
  return text.slice(0, maxLen).trimEnd() + "...";
}

function cleanDescription(text: string): string {
  return text.replace(/^DESCRIPCI[OÓ]N\s*/i, "").trim();
}

export function SearchResultCard({ result, rank }: { result: SearchResult; rank: number }) {
  const openDetail = useSearchStore((s) => s.openDetail);
  const [activeChunk, setActiveChunk] = useState(0);
  const chunk = result.chunks[activeChunk];
  const similarity = scoreToPercent(chunk.score);
  const heritageLabel = HERITAGE_LABELS[result.heritage_type] ?? result.heritage_type;
  const heritageColor = HERITAGE_COLORS[result.heritage_type] ?? "bg-stone-100 text-stone-700";
  const displayName = result.denomination || result.title;
  const totalChunks = result.chunks.length;

  return (
    <div className="rounded-2xl border border-stone-200/60 bg-white p-5 shadow-sm hover:shadow-md transition-shadow">
      <div className="flex items-start gap-4">
        {/* Thumbnail */}
        {result.image_url ? (
          <img
            src={result.image_url}
            alt={displayName}
            className="w-20 h-20 rounded-xl object-cover shrink-0 bg-stone-100"
          />
        ) : (
          <div className="w-20 h-20 rounded-xl bg-stone-100 shrink-0 flex items-center justify-center">
            <svg className="w-8 h-8 text-stone-300" fill="none" viewBox="0 0 24 24" strokeWidth={1} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 21v-8.25M15.75 21v-8.25M8.25 21v-8.25M3 9l9-6 9 6m-1.5 12V10.332A48.36 48.36 0 0 0 12 9.75c-2.551 0-5.056.2-7.5.582V21" />
            </svg>
          </div>
        )}

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className="text-xs font-bold text-stone-300">#{rank}</span>
            <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${heritageColor}`}>
              {heritageLabel}
            </span>
            {result.protection && result.protection.toUpperCase() !== "NO" && (
              <span className="rounded-full px-2.5 py-0.5 text-xs font-medium bg-rose-50 text-rose-700">
                Protegido
              </span>
            )}
          </div>

          <h3 className="font-semibold text-stone-900 text-sm leading-snug mb-1.5 flex items-center gap-1.5">
            <button
              onClick={() => openDetail(result.document_id)}
              className="text-left hover:text-amber-700 transition-colors cursor-pointer"
            >
              {displayName}
            </button>
            {result.url && (
              <a
                href={result.url}
                target="_blank"
                rel="noopener noreferrer"
                className="shrink-0 text-stone-300 hover:text-stone-500 transition-colors"
                title="Ver ficha en IAPH"
                onClick={(e) => e.stopPropagation()}
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
                </svg>
              </a>
            )}
          </h3>

          <div className="flex items-center gap-3 text-xs text-stone-400 mb-2">
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
            {result.latitude != null && result.longitude != null && (
              <span className="text-stone-300">
                {result.latitude.toFixed(4)}, {result.longitude.toFixed(4)}
              </span>
            )}
          </div>

          {result.description && (
            <p
              className="text-xs text-stone-500 leading-relaxed"
              style={{
                overflow: "hidden",
                display: "-webkit-box",
                WebkitLineClamp: 3,
                WebkitBoxOrient: "vertical",
              }}
            >
              {cleanDescription(result.description)}
            </p>
          )}
        </div>

        {/* Score + chunk navigation + detail */}
        <div className="shrink-0 flex flex-col items-center justify-center gap-2">
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

          {/* Chunk navigator — invisible placeholder keeps alignment when single chunk */}
          <div className="flex items-center gap-1">
              <button
                onClick={() => setActiveChunk((i) => Math.max(0, i - 1))}
                disabled={activeChunk === 0}
                className="w-5 h-5 rounded flex items-center justify-center text-stone-400 hover:text-stone-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                aria-label="Chunk anterior"
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
                </svg>
              </button>
              <span className="text-[10px] text-stone-500 font-medium tabular-nums min-w-[2rem] text-center">
                {activeChunk + 1}/{totalChunks}
              </span>
              <button
                onClick={() => setActiveChunk((i) => Math.min(totalChunks - 1, i + 1))}
                disabled={activeChunk === totalChunks - 1}
                className="w-5 h-5 rounded flex items-center justify-center text-stone-400 hover:text-stone-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                aria-label="Chunk siguiente"
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                </svg>
              </button>
          </div>

          {/* Chunk detail tooltip */}
          <div className="relative group/detail">
            <button
              className="w-7 h-7 rounded-full border border-stone-200 flex items-center justify-center text-stone-400 hover:text-stone-600 hover:border-stone-300 transition-colors"
              aria-label="Ver detalle del chunk"
            >
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
              </svg>
            </button>
            <div className="invisible group-hover/detail:visible opacity-0 group-hover/detail:opacity-100 transition-all absolute right-0 top-full mt-1.5 w-80 max-h-64 overflow-y-auto p-3 bg-white border border-stone-200 rounded-xl shadow-lg z-20">
              <div className="flex items-center justify-between mb-2">
                <span className="text-[10px] font-medium text-stone-500 uppercase tracking-wide">
                  Chunk {activeChunk + 1} de {totalChunks}
                </span>
                <span className="text-[10px] text-stone-400 font-mono">
                  {chunk.chunk_id.slice(0, 8)}
                </span>
              </div>
              <div className="flex items-center gap-2 mb-2">
                <span className="text-xs text-stone-600">Similitud:</span>
                <span className="text-xs font-semibold text-amber-600">{similarity}%</span>
                <span className="text-[10px] text-stone-400">
                  (distancia: {chunk.score.toFixed(4)})
                </span>
              </div>
              <p className="text-xs text-stone-500 leading-relaxed border-t border-stone-100 pt-2">
                {truncate(chunk.content, 500)}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
