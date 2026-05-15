"use client";

import { useEffect, useRef, useState } from "react";
import { ScoreThresholdControl } from "./ScoreThresholdControl";

interface ScoreThresholdPopoverProps {
  value: number;
  onChange: (value: number) => void;
  defaultValue?: number;
}

const SlidersIcon = (
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
      d="M10.5 6h9.75M10.5 6a1.5 1.5 0 1 1-3 0m3 0a1.5 1.5 0 1 0-3 0M3.75 6H7.5m3 12h9.75m-9.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-3.75 0H7.5m9-6h3.75m-3.75 0a1.5 1.5 0 0 1-3 0m3 0a1.5 1.5 0 0 0-3 0m-9.75 0h9.75"
    />
  </svg>
);

export function ScoreThresholdPopover({
  value,
  onChange,
  defaultValue = 0.5,
}: ScoreThresholdPopoverProps) {
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

  return (
    <div ref={containerRef} className="relative shrink-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className={`relative flex items-center gap-2 h-full px-4 rounded-2xl border bg-white shadow-sm transition-all ${
          open
            ? "border-green-500 ring-2 ring-green-100 text-stone-700"
            : "border-stone-200 hover:border-stone-300 text-stone-500 hover:text-stone-700"
        }`}
        aria-label="Umbral de similitud"
        aria-expanded={open}
        title="Umbral de similitud"
      >
        {SlidersIcon}
        <span className="text-sm font-semibold text-green-700 tabular-nums">
          {value.toFixed(2)}
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
          aria-label="Ajustar umbral de similitud"
        >
          <ScoreThresholdControl value={value} onChange={onChange} />
        </div>
      )}
    </div>
  );
}
