"use client";

import type { Message, RagSource } from "@/lib/api";

function SourceCard({ source }: { source: RagSource }) {
  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-start gap-2 rounded-lg border border-stone-200 bg-stone-50 px-3 py-2 text-xs hover:border-amber-300 hover:bg-amber-50/50 transition-colors group"
    >
      <svg className="w-3.5 h-3.5 mt-0.5 shrink-0 text-stone-400 group-hover:text-amber-500 transition-colors" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M13.19 8.688a4.5 4.5 0 0 1 1.242 7.244l-4.5 4.5a4.5 4.5 0 0 1-6.364-6.364l1.757-1.757m13.35-.622 1.757-1.757a4.5 4.5 0 0 0-6.364-6.364l-4.5 4.5a4.5 4.5 0 0 0 1.242 7.244" />
      </svg>
      <div className="min-w-0">
        <p className="font-medium text-stone-700 truncate">{source.title}</p>
        <p className="text-stone-400 mt-0.5">
          {source.heritage_type} · {source.province}
        </p>
      </div>
    </a>
  );
}

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-5`}>
      <div className={`max-w-[75%] ${isUser ? "order-2" : "order-1"}`}>
        {!isUser && (
          <div className="flex items-center gap-1.5 mb-1.5 ml-1">
            <div className="h-5 w-5 rounded-md bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
              <span className="text-[10px] font-bold text-white">IA</span>
            </div>
            <span className="text-xs font-medium text-stone-400">Asistente IAPH</span>
          </div>
        )}
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? "bg-gradient-to-br from-amber-600 to-orange-600 text-white rounded-br-md shadow-sm"
              : "bg-white border border-stone-200 text-stone-700 rounded-bl-md shadow-sm"
          }`}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        {message.sources.length > 0 && (
          <div className="mt-2 space-y-1.5 ml-1">
            <p className="text-[11px] font-medium text-stone-400 uppercase tracking-wide">Fuentes</p>
            {message.sources.slice(0, 3).map((src, i) => (
              <SourceCard key={i} source={src} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
