"use client";

import { useEffect, useState } from "react";

export interface LexicalWeightControlProps {
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
  "Más semántica = entiende sinónimos y contexto. Más lexical = prioriza la palabra exacta.";

/**
 * Reusable control for the hybrid search lexical/semantic weight.
 *
 * `value` is the **lexical weight** in [0, 1]. The semantic weight is
 * implicitly `1 - value`. Both weights are shown to the user in the header.
 */
export function LexicalWeightControl({
  value,
  onChange,
  helperText = DEFAULT_HELPER,
  label = "Ponderación de la búsqueda",
  min = 0.0,
  max = 1.0,
  step = 0.05,
  variant = "stacked",
}: LexicalWeightControlProps) {
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

  const semanticWeight = Math.round((1 - value) * 100) / 100;
  const lexicalWeight = Math.round(value * 100) / 100;
  const weightsSummary = `Semántica ${semanticWeight.toFixed(2)} · Lexical ${lexicalWeight.toFixed(2)}`;

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
            d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5"
          />
        </svg>
        <button
          type="button"
          onClick={decrement}
          disabled={value <= min}
          className="w-6 h-6 rounded-md text-stone-400 flex items-center justify-center hover:text-stone-600 hover:bg-stone-100 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          aria-label="Más semántica"
          title={helperText}
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14" />
          </svg>
        </button>
        <span
          className="text-center text-sm font-semibold text-green-700 tabular-nums select-none px-1"
          title={helperText}
        >
          {weightsSummary}
        </span>
        <button
          type="button"
          onClick={increment}
          disabled={value >= max}
          className="w-6 h-6 rounded-md text-stone-400 flex items-center justify-center hover:text-stone-600 hover:bg-stone-100 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
          aria-label="Más lexical"
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
          htmlFor="lexical-weight-input"
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
            aria-label="Más semántica"
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14" />
            </svg>
          </button>
          <input
            id="lexical-weight-input"
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
            aria-label="Peso lexical"
          />
          <button
            type="button"
            onClick={increment}
            disabled={value >= max}
            className="w-6 h-6 rounded-md text-stone-400 flex items-center justify-center hover:text-stone-600 hover:bg-stone-100 transition-colors disabled:opacity-30 disabled:cursor-not-allowed"
            aria-label="Más lexical"
          >
            <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
            </svg>
          </button>
        </div>
      </div>
      <div className="text-center text-xs font-semibold text-green-700 tabular-nums select-none">
        {weightsSummary}
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
        <span className="text-stone-500">Más semántica ← → más lexical</span>
        <span>{max.toFixed(2)}</span>
      </div>
      {helperText === DEFAULT_HELPER ? (
        <div className="text-xs text-stone-500 leading-snug text-center space-y-0.5">
          <p>
            <strong className="font-semibold text-stone-700">Más semántica</strong>
            {" → entiende sinónimos y contexto."}
          </p>
          <p>
            <strong className="font-semibold text-stone-700">Más lexical</strong>
            {" → prioriza la palabra exacta."}
          </p>
        </div>
      ) : (
        <p className="text-xs text-stone-500 leading-snug text-center">{helperText}</p>
      )}
    </div>
  );
}
