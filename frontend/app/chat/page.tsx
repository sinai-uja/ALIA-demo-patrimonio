"use client";

import { useEffect, useRef } from "react";
import { useChatStore } from "@/store/chat";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { ChatInput } from "@/components/chat/ChatInput";

export default function ChatPage() {
  const {
    sessions, activeSessionId, messages, loading, sending,
    loadSessions, createSession, selectSession, deleteSession, sendMessage,
  } = useChatStore();

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { loadSessions(); }, [loadSessions]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const handleNewSession = async () => {
    await createSession();
  };

  const handleSend = async (content: string) => {
    if (!activeSessionId) {
      await createSession();
    }
    await sendMessage(content);
  };

  return (
    <div className="flex h-[calc(100vh-7rem)] gap-4">
      {/* Sidebar — sessions */}
      <aside className="w-64 shrink-0 flex flex-col gap-2">
        <button
          onClick={handleNewSession}
          className="w-full rounded-xl bg-amber-700 py-2 text-sm font-medium text-white hover:bg-amber-800 transition"
        >
          + Nueva conversación
        </button>
        <div className="flex-1 overflow-y-auto space-y-1">
          {sessions.map((s) => (
            <div
              key={s.id}
              className={`group flex items-center justify-between rounded-lg px-3 py-2 cursor-pointer text-sm transition ${
                s.id === activeSessionId
                  ? "bg-amber-100 text-amber-900"
                  : "hover:bg-gray-100 text-gray-700"
              }`}
              onClick={() => selectSession(s.id)}
            >
              <span className="truncate flex-1">{s.title}</span>
              <button
                className="ml-1 hidden group-hover:block text-gray-400 hover:text-red-500"
                onClick={(e) => { e.stopPropagation(); deleteSession(s.id); }}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </aside>

      {/* Main chat */}
      <div className="flex flex-1 flex-col min-w-0">
        <div className="flex-1 overflow-y-auto px-2 py-4">
          {!activeSessionId && (
            <div className="flex h-full items-center justify-center text-gray-400 text-sm">
              Crea una nueva conversación para empezar
            </div>
          )}
          {loading && (
            <div className="text-center text-gray-400 text-sm py-8">Cargando…</div>
          )}
          {messages.map((m) => <MessageBubble key={m.id} message={m} />)}
          {sending && (
            <div className="flex justify-start mb-4">
              <div className="rounded-2xl rounded-bl-sm bg-white border border-gray-200 px-4 py-3 text-sm text-gray-400 shadow-sm">
                Generando respuesta…
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
        <div className="pt-2">
          <ChatInput onSend={handleSend} disabled={sending} />
        </div>
      </div>
    </div>
  );
}
