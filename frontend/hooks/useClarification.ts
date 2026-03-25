"use client";

import { useState, useCallback, useRef } from "react";
import type { DetectedEntity } from "@/lib/api";
import type { ActiveFilter, EntityInfo } from "@/components/shared/SmartInput";
import { HERITAGE_TYPE_LABELS } from "@/components/shared/SmartInput";

export interface ClarificationGroup {
  matchedText: string;
  entities: EntityInfo[];
}

export type ClarificationChoice =
  | { kind: "select"; entities: EntityInfo[] }
  | { kind: "skip" };

interface ClarificationState {
  active: boolean;
  groups: ClarificationGroup[];
  resolved: Map<number, ClarificationChoice>;
}

const INITIAL_STATE: ClarificationState = {
  active: false,
  groups: [],
  resolved: new Map(),
};

export function useClarification(params: {
  detectedEntities: DetectedEntity[];
  activeFilters: ActiveFilter[];
  onAddFilters: (filters: ActiveFilter[]) => void;
  onExecute: () => void;
}) {
  const [state, setState] = useState<ClarificationState>(INITIAL_STATE);
  const paramsRef = useRef(params);
  paramsRef.current = params;

  const startClarification = useCallback((): boolean => {
    const { detectedEntities, activeFilters } = paramsRef.current;

    const pending = detectedEntities.filter(
      (e) =>
        !activeFilters.some(
          (f) =>
            f.type === (e.entity_type as ActiveFilter["type"]) &&
            f.value === e.value,
        ),
    );

    if (pending.length === 0) return false;

    const groupMap = new Map<string, EntityInfo[]>();
    for (const e of pending) {
      const key = e.matched_text.toLowerCase();
      if (!groupMap.has(key)) groupMap.set(key, []);
      groupMap.get(key)!.push({
        entityType: e.entity_type,
        value: e.value,
        displayLabel: e.display_label,
        matchedText: e.matched_text,
      });
    }

    const groups: ClarificationGroup[] = [];
    for (const [matchedText, entities] of groupMap) {
      groups.push({ matchedText, entities });
    }

    setState({ active: true, groups, resolved: new Map() });
    return true;
  }, []);

  const finalize = useCallback(
    (resolved: Map<number, ClarificationChoice>) => {
      const filtersToAdd: ActiveFilter[] = [];
      for (const [, choice] of resolved) {
        if (choice.kind === "select") {
          for (const ent of choice.entities) {
            const filterType = ent.entityType as ActiveFilter["type"];
            let label = ent.value;
            if (filterType === "heritage_type") {
              label = HERITAGE_TYPE_LABELS[ent.value] ?? ent.value;
            }
            filtersToAdd.push({
              type: filterType,
              value: ent.value,
              label,
              matchedText: ent.matchedText,
            });
          }
        }
      }
      if (filtersToAdd.length > 0) {
        paramsRef.current.onAddFilters(filtersToAdd);
      }
      setState(INITIAL_STATE);
      paramsRef.current.onExecute();
    },
    [],
  );

  const resolveGroup = useCallback(
    (groupIndex: number, choice: ClarificationChoice) => {
      setState((prev) => {
        const newResolved = new Map(prev.resolved);
        newResolved.set(groupIndex, choice);

        if (newResolved.size === prev.groups.length) {
          // Schedule finalize after state update
          setTimeout(() => finalize(newResolved), 0);
          return INITIAL_STATE;
        }

        return { ...prev, resolved: newResolved };
      });
    },
    [finalize],
  );

  const skipAll = useCallback(() => {
    setState(INITIAL_STATE);
    paramsRef.current.onExecute();
  }, []);

  const dismiss = useCallback(() => {
    setState(INITIAL_STATE);
  }, []);

  return {
    active: state.active,
    groups: state.groups,
    resolved: state.resolved,
    startClarification,
    resolveGroup,
    skipAll,
    dismiss,
  };
}
