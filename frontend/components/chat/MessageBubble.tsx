"use client";

import type { Message, RagSource } from "@/lib/api";
import { type ReactNode } from "react";

function SourceCard({ index, source }: { index: number; source: RagSource }) {
  return (
    <a
      id={`source-${index}`}
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-start gap-2 rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs hover:border-green-300 hover:bg-green-50/50 transition-colors group"
    >
      <span className="shrink-0 mt-0.5 flex items-center justify-center h-4 w-4 rounded bg-green-100 text-green-700 text-[10px] font-bold">
        {index}
      </span>
      <div className="min-w-0">
        <p className="font-medium text-stone-700 truncate">{source.title}</p>
        <p className="text-stone-400 mt-0.5">
          {source.heritage_type} · {source.province}
          {source.municipality ? ` · ${source.municipality}` : ""}
        </p>
      </div>
    </a>
  );
}

/** Replace [N] references in text with clickable links that scroll to the source card. */
function renderContentWithRefs(content: string, sources: RagSource[]): ReactNode[] {
  const parts = content.split(/(\[\d+\])/g);
  return parts.map((part, i) => {
    const match = part.match(/^\[(\d+)\]$/);
    if (match) {
      const idx = parseInt(match[1], 10);
      const source = sources[idx - 1];
      if (source) {
        return (
          <a
            key={i}
            href={source.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center justify-center h-4 min-w-[1rem] px-0.5 rounded bg-green-100 text-green-700 text-[10px] font-bold no-underline hover:bg-green-200 transition-colors cursor-pointer align-baseline"
            title={source.title}
          >
            {idx}
          </a>
        );
      }
    }
    return <span key={i}>{part}</span>;
  });
}

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-5`}>
      <div className={`max-w-[75%] ${isUser ? "order-2" : "order-1"}`}>
        {!isUser && (
          <div className="flex items-center gap-1.5 mb-1.5 ml-1">
            <div className="h-5 w-5 rounded-md bg-gradient-to-br from-green-600 to-emerald-700 flex items-center justify-center">
              <span className="text-[10px] font-bold text-white">IA</span>
            </div>
            <span className="text-xs font-medium text-stone-400">Asistente Patrimonio</span>
          </div>
        )}
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? "bg-gradient-to-br from-green-700 to-emerald-700 text-white rounded-br-md shadow-sm"
              : "bg-white border border-stone-200 text-stone-700 rounded-bl-md shadow-sm"
          }`}
        >
          <p className="whitespace-pre-wrap">
            {isUser || message.sources.length === 0
              ? message.content
              : renderContentWithRefs(message.content, message.sources)}
          </p>
        </div>
        {message.sources.length > 0 && (
          <div className="mt-2 space-y-1.5 ml-1">
            <p className="text-[11px] font-medium text-stone-400 uppercase tracking-wide">Fuentes</p>
            {message.sources.map((src, i) => (
              <SourceCard key={i} index={i + 1} source={src} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
