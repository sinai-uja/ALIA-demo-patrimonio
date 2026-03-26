"use client";

import { useState, useRef, type KeyboardEvent } from "react";

interface Props {
  onSend: (content: string) => void;
  disabled?: boolean;
  placeholder?: string;
}

export function ChatInput({ onSend, disabled, placeholder }: Props) {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSend = () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setValue("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInput = () => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  };

  return (
    <div className="flex items-center gap-3 rounded-2xl border border-stone-200 bg-white px-4 py-2.5 shadow-sm focus-within:border-green-500 focus-within:ring-2 focus-within:ring-green-100 transition-all">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        rows={1}
        disabled={disabled}
        placeholder={placeholder ?? "Pregunta sobre el patrimonio histórico andaluz..."}
        className="flex-1 resize-none bg-transparent text-sm leading-5 outline-none placeholder:text-stone-400 disabled:opacity-50 py-0.5"
      />
      <button
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        className="shrink-0 flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-green-600 to-emerald-700 text-white shadow-sm transition hover:shadow-md disabled:opacity-30 disabled:shadow-none"
      >
        {disabled ? (
          <div className="flex gap-0.5">
            <span className="typing-dot h-1 w-1 rounded-full bg-white" />
            <span className="typing-dot h-1 w-1 rounded-full bg-white" />
            <span className="typing-dot h-1 w-1 rounded-full bg-white" />
          </div>
        ) : (
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
          </svg>
        )}
      </button>
    </div>
  );
}
