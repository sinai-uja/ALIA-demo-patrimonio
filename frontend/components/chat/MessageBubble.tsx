"use client";

import type { Message, RagSource } from "@/lib/api";

function SourceCard({ source }: { source: RagSource }) {
  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="block rounded border border-amber-200 bg-amber-50 px-3 py-2 text-xs hover:bg-amber-100 transition-colors"
    >
      <p className="font-medium text-amber-900 truncate">{source.title}</p>
      <p className="text-amber-600 mt-0.5">
        {source.heritage_type} · {source.province} · {(source.score * 100).toFixed(0)}% relevancia
      </p>
    </a>
  );
}

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}>
      <div className={`max-w-[80%] ${isUser ? "order-2" : "order-1"}`}>
        {!isUser && (
          <p className="text-xs text-gray-500 mb-1 ml-1">Asistente IAPH</p>
        )}
        <div
          className={`rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? "bg-amber-700 text-white rounded-br-sm"
              : "bg-white border border-gray-200 text-gray-800 rounded-bl-sm shadow-sm"
          }`}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>
        {message.sources.length > 0 && (
          <div className="mt-2 space-y-1.5">
            <p className="text-xs text-gray-400 ml-1">Fuentes:</p>
            {message.sources.slice(0, 3).map((src, i) => (
              <SourceCard key={i} source={src} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
