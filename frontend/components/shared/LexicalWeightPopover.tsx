"use client";

import { useEffect, useRef, useState } from "react";
import { LexicalWeightControl } from "./LexicalWeightControl";

interface LexicalWeightPopoverProps {
  value: number;
  onChange: (value: number) => void;
  defaultValue?: number;
}

const ScalesIcon = (
  <svg
    className="w-5 h-5"
    fill="none"
    viewBox="0 0 24 24"
    strokeWidth={1.5}
    stroke="currentColor"
    aria-hidden="true"
  >
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M12 3v18m-9-9h18M5.25 7.5l-2.25 6h4.5l-2.25-6Zm13.5 0-2.25 6h4.5l-2.25-6Z"
    />
  </svg>
);

export function LexicalWeightPopover({
  value,
  onChange,
  defaultValue = 0.5,
}: LexicalWeightPopoverProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const modified = Math.abs(value - defaultValue) > 0.001;

  useEffect(() => {
    if (!open) return;
    const handleMouseDown = (e: MouseEvent) => {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    document.addEventListener("mousedown", handleMouseDown);
    document.addEventListener("keydown", handleKey);
    return () => {
      document.removeEventListener("mousedown", handleMouseDown);
      document.removeEventListener("keydown", handleKey);
    };
  }, [open]);

  const semanticWeight = Math.round((1 - value) * 100) / 100;
  const lexicalWeight = Math.round(value * 100) / 100;
  const summary = `${semanticWeight.toFixed(2)} / ${lexicalWeight.toFixed(2)}`;

  return (
    <div ref={containerRef} className="relative shrink-0 flex">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`relative flex items-center gap-2 px-4 rounded-2xl border bg-white shadow-sm transition-all ${
          open
            ? "border-green-500 ring-2 ring-green-100 text-stone-700"
            : "border-stone-200 hover:border-stone-300 text-stone-500 hover:text-stone-700"
        }`}
        aria-label="Ponderación de la búsqueda"
        aria-expanded={open}
        title="Ponderación semántica / lexical"
      >
        {ScalesIcon}
        <span className="text-sm font-semibold text-green-700 tabular-nums">
          {summary}
        </span>
        {modified && (
          <span
            className="absolute -top-1 -right-1 h-2 w-2 rounded-full bg-green-600 ring-2 ring-white"
            aria-hidden="true"
          />
        )}
      </button>

      {open && (
        <div
          className="absolute right-0 top-full mt-2 w-72 z-30 rounded-lg border border-stone-200 bg-white shadow-lg p-3"
          role="dialog"
          aria-label="Ajustar ponderación de la búsqueda"
        >
          <LexicalWeightControl value={value} onChange={onChange} />
        </div>
      )}
    </div>
  );
}
