"use client";

import { useEffect, useState } from "react";

export interface ScoreThresholdControlProps {
  value: number;
  onChange: (value: number) => void;
  helperText?: string;
  label?: string;
  min?: number;
  max?: number;
  step?: number;
  /** Visual layout: "stacked" (label + slider + helper, full block) or "inline" (compact, beside other controls). */
  variant?: "stacked" | "inline";
}

const DEFAULT_HELPER =
  "Más bajo = resultados más cercanos. Más alto = más resultados, posiblemente menos relevantes.";

/**
 * Reusable control for the similarity score threshold.
 *
 * Note: the value is technically a cosine **distance** cutoff
 * (lower = stricter, more similar). The label "Umbral de similitud"
 * is preserved to match user mental model.
 */
export function ScoreThresholdControl({
  value,
  onChange,
  helperText = DEFAULT_HELPER,
  label = "Umbral de similitud",
  min = 0.10,
  max = 1.00,
  step = 0.05,
  variant = "stacked",
}: ScoreThresholdControlProps) {
  // Local input mirror so users can type freely before committing.
  const [text, setText] = useState(value.toFixed(2));

  useEffect(() => {
    setText(value.toFixed(2));
  }, [value]);

  const clamp = (n: number) => Math.min(max, Math.max(min, n));

  const commit = (raw: string) => {
    const parsed = Number(raw.replace(",", "."));
    if (Number.isFinite(parsed)) {
      const next = Math.round(clamp(parsed) * 100) / 100;
      onChange(next);
      setText(next.toFixed(2));
    } else {
      setText(value.toFixed(2));
    }
  };

  const decrement = () => onChange(Math.round(clamp(value - step) * 100) / 100);
  const increment = () => onChange(Math.round(clamp(value + step) * 100) / 100);

  if (variant === "inline") {
    return (
      <div className="flex items-center gap-1 border-l border-stone-200 pl-3 ml-1 shrink-0">
        <svg
          className="w-4 h-4 text-stone-400 shrink-0 mr-0.5"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M3 7.5h13.5m0 0L12 3m4.5 4.5L12 12m8.25 4.5H6.75m0 0L11.25 12m-4.5 4.5L11.25 21"
          />
        </svg>
        <button
          type="button"
          onClick={decrement}
          disabled={value <= min}
          className="w-6 h-6 rounded-md text-stone-400 flex items-center justify-center hover:text-stone-600 hover:bg-stone-100 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          aria-label="Disminuir umbral"
          title={helperText}
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14" />
          </svg>
        </button>
        <span
          className="w-10 text-center text-sm font-semibold text-green-700 tabular-nums select-none"
          title={helperText}
        >
          {value.toFixed(2)}
        </span>
        <button
          type="button"
          onClick={increment}
          disabled={value >= max}
          className="w-6 h-6 rounded-md text-stone-400 flex items-center justify-center hover:text-stone-600 hover:bg-stone-100 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          aria-label="Aumentar umbral"
          title={helperText}
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
          </svg>
        </button>
        <div className="w-px h-5 bg-stone-200 ml-1 shrink-0" />
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between gap-2">
        <label
          htmlFor="score-threshold-input"
          className="text-sm font-medium text-stone-700"
        >
          {label}
        </label>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={decrement}
            disabled={value <= min}
            className="w-6 h-6 rounded-md text-stone-400 flex items-center justify-center hover:text-stone-600 hover:bg-stone-100 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            aria-label="Disminuir umbral"
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14" />
            </svg>
          </button>
          <input
            id="score-threshold-input"
            type="number"
            inputMode="decimal"
            min={min}
            max={max}
            step={step}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onBlur={(e) => commit(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                commit((e.target as HTMLInputElement).value);
                (e.target as HTMLInputElement).blur();
              }
            }}
            className="w-16 rounded border border-stone-200 px-1.5 py-0.5 text-center text-xs font-semibold text-green-700 tabular-nums focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500"
          />
          <button
            type="button"
            onClick={increment}
            disabled={value >= max}
            className="w-6 h-6 rounded-md text-stone-400 flex items-center justify-center hover:text-stone-600 hover:bg-stone-100 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            aria-label="Aumentar umbral"
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
          </button>
        </div>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full accent-green-600"
        aria-label={label}
      />
      <div className="flex justify-between text-[10px] text-stone-400 tabular-nums">
        <span>{min.toFixed(2)}</span>
        <span className="text-stone-500">más exigente ← → más resultados</span>
        <span>{max.toFixed(2)}</span>
      </div>
      {helperText === DEFAULT_HELPER ? (
        <div className="text-xs text-stone-500 leading-snug text-center space-y-0.5">
          <p>
            <strong className="font-semibold text-stone-700">Más bajo</strong>
            {" = resultados más cercanos."}
          </p>
          <p>
            <strong className="font-semibold text-stone-700">Más alto</strong>
            {" = más resultados, posiblemente menos relevantes."}
          </p>
        </div>
      ) : (
        <p className="text-xs text-stone-500 leading-snug text-center">{helperText}</p>
      )}
    </div>
  );
}
