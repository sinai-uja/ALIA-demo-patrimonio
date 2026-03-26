"use client";

import type { ClarificationGroup, ClarificationChoice } from "@/hooks/useClarification";
import type { EntityInfo } from "@/components/shared/SmartInput";
import {
  TYPE_LABELS,
  HERITAGE_TYPE_LABELS,
  TOOLTIP_COLORS,
} from "@/components/shared/SmartInput";

interface ClarificationPanelProps {
  groups: ClarificationGroup[];
  resolved: Map<number, ClarificationChoice>;
  onResolve: (groupIndex: number, choice: ClarificationChoice) => void;
  onSkipAll: () => void;
  onDismiss: () => void;
  executeLabel?: string;
}

const CHECK_ICON = (
  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
    <path strokeLinecap="round" strokeLinejoin="round" d="m4.5 12.75 6 6 9-13.5" />
  </svg>
);

function ResolvedSummary({ choice, group }: { choice: ClarificationChoice; group: ClarificationGroup }) {
  if (choice.kind === "skip") {
    return (
      <div className="flex items-center gap-2 text-xs text-stone-400 py-1.5 px-3">
        <span className="text-emerald-500">{CHECK_ICON}</span>
        <span>«{group.matchedText}» — buscar por similaridad</span>
      </div>
    );
  }

  const labels = choice.entities.map((e) => {
    const typeLabel = TYPE_LABELS[e.entityType] ?? e.entityType;
    const valueLabel =
      e.entityType === "heritage_type"
        ? HERITAGE_TYPE_LABELS[e.value] ?? e.value
        : e.value;
    return `${typeLabel}: ${valueLabel}`;
  });

  return (
    <div className="flex items-center gap-2 text-xs text-stone-400 py-1.5 px-3">
      <span className="text-emerald-500">{CHECK_ICON}</span>
      <span>«{group.matchedText}» — {labels.join(", ")}</span>
    </div>
  );
}

function selectSome(entities: EntityInfo[]): ClarificationChoice {
  return { kind: "select", entities };
}

function GroupCard({
  group,
  index,
  onResolve,
}: {
  group: ClarificationGroup;
  index: number;
  onResolve: (index: number, choice: ClarificationChoice) => void;
}) {
  const geoEntities = group.entities.filter(
    (e) => e.entityType === "province" || e.entityType === "municipality",
  );
  const heritageEntities = group.entities.filter(
    (e) => e.entityType === "heritage_type",
  );

  const hasProvince = geoEntities.some((e) => e.entityType === "province");
  const hasMunicipality = geoEntities.some((e) => e.entityType === "municipality");
  const isGeoAmbiguous = hasProvince && hasMunicipality;

  return (
    <div className="bg-stone-50 border border-stone-200 rounded-xl p-4 space-y-3 animate-in fade-in slide-in-from-top-2 duration-200">
      {/* Geographic entities */}
      {geoEntities.length > 0 && (
        <div className="space-y-2.5">
          <p className="text-sm text-stone-700">
            He detectado <span className="font-semibold text-stone-900">&laquo;{group.matchedText}&raquo;</span> en tu consulta.
            {isGeoAmbiguous
              ? " ¿Te refieres a..."
              : hasProvince
                ? " ¿Quieres filtrar por esta provincia?"
                : " ¿Quieres filtrar por este municipio?"}
          </p>
          <div className="flex flex-wrap gap-2">
            {isGeoAmbiguous ? (
              <>
                {geoEntities.map((e) => {
                  const color = TOOLTIP_COLORS[e.entityType] ?? "bg-stone-100 text-stone-800";
                  return (
                    <button
                      key={`${e.entityType}-${e.value}`}
                      onClick={() => onResolve(index, selectSome([e]))}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${color}`}
                    >
                      {TYPE_LABELS[e.entityType]}: {e.value}
                    </button>
                  );
                })}
                <button
                  onClick={() => onResolve(index, selectSome(geoEntities))}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium bg-stone-200 text-stone-700 hover:bg-stone-300 transition-colors"
                >
                  Ambos
                </button>
                <button
                  onClick={() => {
                    if (heritageEntities.length === 0) {
                      onResolve(index, { kind: "skip" });
                    } else {
                      // Skip only geo, but we handle heritage below — skip geo part
                      onResolve(index, { kind: "skip" });
                    }
                  }}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium text-stone-500 hover:bg-stone-100 transition-colors"
                >
                  Ninguno
                </button>
              </>
            ) : (
              <>
                <button
                  onClick={() => onResolve(index, selectSome(geoEntities))}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${TOOLTIP_COLORS[geoEntities[0].entityType]}`}
                >
                  Si, filtrar por {TYPE_LABELS[geoEntities[0].entityType].toLowerCase()}
                </button>
                <button
                  onClick={() => onResolve(index, { kind: "skip" })}
                  className="px-3 py-1.5 rounded-lg text-xs font-medium text-stone-500 hover:bg-stone-100 transition-colors"
                >
                  No, buscar por similaridad
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* Heritage type entities (when no geo in same group) */}
      {heritageEntities.length > 0 && geoEntities.length === 0 && (
        <div className="space-y-2.5">
          {heritageEntities.map((e) => {
            const label = HERITAGE_TYPE_LABELS[e.value] ?? e.value;
            return (
              <div key={`${e.entityType}-${e.value}`}>
                <p className="text-sm text-stone-700">
                  He detectado <span className="font-semibold text-stone-900">&laquo;{group.matchedText}&raquo;</span>.
                  {" "}¿Quieres filtrar por <span className="font-medium text-green-700">{label}</span>?
                </p>
                <div className="flex gap-2 mt-2">
                  <button
                    onClick={() => onResolve(index, selectSome([e]))}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium bg-green-100 text-green-800 hover:bg-green-200 transition-colors"
                  >
                    Si, filtrar
                  </button>
                  <button
                    onClick={() => onResolve(index, { kind: "skip" })}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium text-stone-500 hover:bg-stone-100 transition-colors"
                  >
                    No, buscar por similaridad
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export function ClarificationPanel({
  groups,
  resolved,
  onResolve,
  onSkipAll,
  onDismiss,
  executeLabel = "Buscar",
}: ClarificationPanelProps) {
  // Find the first unresolved group
  const currentIndex = groups.findIndex((_, i) => !resolved.has(i));

  return (
    <div className="mt-3 space-y-2 animate-in fade-in slide-in-from-top-3 duration-300">
      {/* Assistant intro */}
      <div className="flex items-start gap-2.5">
        <div className="w-6 h-6 rounded-full bg-green-100 flex items-center justify-center shrink-0 mt-0.5">
          <svg className="w-3.5 h-3.5 text-green-700" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09ZM18.259 8.715 18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 0 0-2.455 2.456Z" />
          </svg>
        </div>
        <p className="text-sm text-stone-600 pt-0.5">
          Antes de buscar, tengo algunas preguntas sobre tu consulta:
        </p>
      </div>

      {/* Resolved groups — compact summaries */}
      {groups.map((group, i) => {
        const choice = resolved.get(i);
        if (!choice) return null;
        return <ResolvedSummary key={i} choice={choice} group={group} />;
      })}

      {/* Current unresolved group */}
      {currentIndex >= 0 && (
        <GroupCard
          group={groups[currentIndex]}
          index={currentIndex}
          onResolve={onResolve}
        />
      )}

      {/* Bottom actions */}
      <div className="flex items-center justify-between pt-1">
        <button
          onClick={onSkipAll}
          className="text-xs text-stone-400 hover:text-stone-600 transition-colors flex items-center gap-1.5"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 8.689c0-.864.933-1.406 1.683-.977l7.108 4.061a1.125 1.125 0 0 1 0 1.954l-7.108 4.061A1.125 1.125 0 0 1 3 16.811V8.69ZM12.75 8.689c0-.864.933-1.406 1.683-.977l7.108 4.061a1.125 1.125 0 0 1 0 1.954l-7.108 4.061a1.125 1.125 0 0 1-1.683-.977V8.69Z" />
          </svg>
          {executeLabel} directamente
        </button>
        <button
          onClick={onDismiss}
          className="text-xs text-stone-400 hover:text-stone-600 transition-colors"
        >
          Cancelar
        </button>
      </div>
    </div>
  );
}
