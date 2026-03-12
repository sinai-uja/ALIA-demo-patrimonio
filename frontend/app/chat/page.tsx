"use client";

import { useEffect, useRef, useState } from "react";
import { useChatStore } from "@/store/chat";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { ChatInput } from "@/components/chat/ChatInput";

function SessionItem({
  id,
  title,
  active,
  onSelect,
  onDelete,
  onRename,
}: {
  id: string;
  title: string;
  active: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onRename: (title: string) => void;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(title);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing) inputRef.current?.select();
  }, [editing]);

  const commit = () => {
    setEditing(false);
    const trimmed = draft.trim();
    if (trimmed && trimmed !== title) onRename(trimmed);
    else setDraft(title);
  };

  return (
    <div
      className={`group flex items-center gap-2 rounded-lg px-3 py-2 cursor-pointer text-sm transition-all ${
        active
          ? "bg-amber-50 text-amber-800 border border-amber-200/60"
          : "text-stone-600 hover:bg-stone-100 border border-transparent"
      }`}
      onClick={() => !editing && onSelect()}
    >
      {editing ? (
        <input
          ref={inputRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onBlur={commit}
          onKeyDown={(e) => {
            if (e.key === "Enter") commit();
            if (e.key === "Escape") { setDraft(title); setEditing(false); }
          }}
          className="flex-1 min-w-0 bg-transparent outline-none text-sm"
          onClick={(e) => e.stopPropagation()}
        />
      ) : (
        <span
          className="truncate flex-1"
          onDoubleClick={(e) => { e.stopPropagation(); setEditing(true); }}
        >
          {title}
        </span>
      )}
      {!editing && (
        <div className="flex items-center gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            className="p-0.5 text-stone-400 hover:text-amber-600 transition-colors"
            onClick={(e) => { e.stopPropagation(); setEditing(true); }}
            title="Renombrar"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8.8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Zm0 0L19.5 7.125" />
            </svg>
          </button>
          <button
            className="p-0.5 text-stone-400 hover:text-red-500 transition-colors"
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
            title="Eliminar"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
            </svg>
          </button>
        </div>
      )}
    </div>
  );
}

export default function ChatPage() {
  const {
    sessions, activeSessionId, messages, loading, sending,
    loadSessions, createSession, selectSession, deleteSession, renameSession, sendMessage,
  } = useChatStore();

  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => { loadSessions(); }, [loadSessions]);
  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const handleSend = async (content: string) => {
    if (!activeSessionId) {
      await createSession();
    }
    await sendMessage(content);
  };

  return (
    <div className="flex h-[calc(100vh-3.5rem)]">
      {/* Sidebar */}
      <aside className="w-72 shrink-0 flex flex-col border-r border-stone-200/60 bg-white">
        <div className="p-3">
          <button
            onClick={() => createSession()}
            className="w-full flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-amber-500 to-orange-600 py-2.5 text-sm font-medium text-white shadow-sm hover:shadow-md transition-all"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
            Nueva conversación
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-3 pb-3 space-y-0.5">
          {sessions.map((s) => (
            <SessionItem
              key={s.id}
              id={s.id}
              title={s.title}
              active={s.id === activeSessionId}
              onSelect={() => selectSession(s.id)}
              onDelete={() => deleteSession(s.id)}
              onRename={(title) => renameSession(s.id, title)}
            />
          ))}
        </div>
      </aside>

      {/* Main chat */}
      <div className="flex flex-1 flex-col min-w-0 bg-stone-50/50">
        <div className="flex-1 overflow-y-auto px-6 py-6">
          {!activeSessionId && !loading && (
            <div className="flex h-full flex-col items-center justify-center text-center">
              <div className="h-16 w-16 rounded-2xl bg-gradient-to-br from-amber-100 to-orange-100 flex items-center justify-center mb-4">
                <svg className="w-8 h-8 text-amber-600" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.129.166 2.27.293 3.423.379.35.026.67.21.865.501L12 21l2.755-4.133a1.14 1.14 0 0 1 .865-.501 48.172 48.172 0 0 0 3.423-.379c1.584-.233 2.707-1.626 2.707-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z" />
                </svg>
              </div>
              <h2 className="text-lg font-semibold text-stone-700 mb-1">Patrimonio Histórico Andaluz</h2>
              <p className="text-sm text-stone-400 max-w-sm">
                Crea una conversación para explorar el patrimonio cultural de Andalucía
              </p>
            </div>
          )}
          {loading && (
            <div className="flex h-full items-center justify-center">
              <div className="flex gap-1">
                <span className="typing-dot h-2 w-2 rounded-full bg-amber-400" />
                <span className="typing-dot h-2 w-2 rounded-full bg-amber-400" />
                <span className="typing-dot h-2 w-2 rounded-full bg-amber-400" />
              </div>
            </div>
          )}
          {messages.map((m) => <MessageBubble key={m.id} message={m} />)}
          {sending && (
            <div className="flex justify-start mb-5">
              <div className="flex items-center gap-1.5 ml-1">
                <div className="h-5 w-5 rounded-md bg-gradient-to-br from-amber-500 to-orange-600 flex items-center justify-center">
                  <span className="text-[10px] font-bold text-white">IA</span>
                </div>
                <span className="text-xs font-medium text-stone-400">Asistente IAPH</span>
              </div>
            </div>
          )}
          {sending && (
            <div className="flex justify-start mb-5">
              <div className="rounded-2xl rounded-bl-md bg-white border border-stone-200 px-4 py-3 shadow-sm">
                <div className="flex gap-1">
                  <span className="typing-dot h-1.5 w-1.5 rounded-full bg-stone-400" />
                  <span className="typing-dot h-1.5 w-1.5 rounded-full bg-stone-400" />
                  <span className="typing-dot h-1.5 w-1.5 rounded-full bg-stone-400" />
                </div>
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
        <div className="px-6 pb-4">
          <ChatInput onSend={handleSend} disabled={sending} />
          <p className="text-center text-[11px] text-stone-400 mt-2">
            Respuestas generadas por IA · Verifica la información con las fuentes
          </p>
        </div>
      </div>
    </div>
  );
}
