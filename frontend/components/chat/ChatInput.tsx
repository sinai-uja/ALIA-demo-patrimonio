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
    <div className="flex items-end gap-2 rounded-2xl border border-gray-300 bg-white px-4 py-3 shadow-sm focus-within:border-amber-500 focus-within:ring-1 focus-within:ring-amber-500 transition">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        onInput={handleInput}
        rows={1}
        disabled={disabled}
        placeholder={placeholder ?? "Pregunta sobre el patrimonio histórico andaluz…"}
        className="flex-1 resize-none bg-transparent text-sm outline-none placeholder:text-gray-400 disabled:opacity-50"
      />
      <button
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        className="shrink-0 rounded-xl bg-amber-700 px-3 py-1.5 text-sm font-medium text-white transition hover:bg-amber-800 disabled:opacity-40"
      >
        {disabled ? "…" : "Enviar"}
      </button>
    </div>
  );
}
