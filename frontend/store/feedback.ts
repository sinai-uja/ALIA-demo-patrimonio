import { create } from "zustand";
import { feedback as feedbackApi } from "@/lib/api";

interface FeedbackState {
  feedbacks: Record<string, number>; // key: "targetType:targetId", value: +1/-1

  submitFeedback: (
    targetType: "route" | "search",
    targetId: string,
    value: 1 | -1,
    metadata?: Record<string, unknown>
  ) => Promise<void>;
  loadFeedback: (targetType: string, targetId: string) => Promise<void>;
  loadFeedbackBatch: (targetType: string, targetIds: string[]) => Promise<void>;
}

export const useFeedbackStore = create<FeedbackState>((set, get) => ({
  feedbacks: {},

  submitFeedback: async (targetType, targetId, value, metadata) => {
    const key = `${targetType}:${targetId}`;
    const current = get().feedbacks[key];

    if (current === value) {
      // Toggle off — optimistic removal
      set((s) => {
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        const { [key]: _removed, ...rest } = s.feedbacks;
        return { feedbacks: rest };
      });
      try {
        await feedbackApi.delete(targetType, targetId);
      } catch {
        /* ignore */
      }
    } else {
      // Set or change — optimistic update
      set((s) => ({ feedbacks: { ...s.feedbacks, [key]: value } }));
      try {
        await feedbackApi.submit({
          target_type: targetType,
          target_id: targetId,
          value,
          metadata,
        });
      } catch {
        // Revert on error
        if (current !== undefined) {
          set((s) => ({ feedbacks: { ...s.feedbacks, [key]: current } }));
        } else {
          set((s) => {
            // eslint-disable-next-line @typescript-eslint/no-unused-vars
            const { [key]: _removed, ...rest } = s.feedbacks;
            return { feedbacks: rest };
          });
        }
      }
    }
  },

  loadFeedback: async (targetType, targetId) => {
    try {
      const res = await feedbackApi.get(targetType, targetId);
      set((s) => ({
        feedbacks: { ...s.feedbacks, [`${targetType}:${targetId}`]: res.value },
      }));
    } catch {
      // 404 = no feedback, ignore
    }
  },

  loadFeedbackBatch: async (targetType, targetIds) => {
    if (targetIds.length === 0) return;
    try {
      const res = await feedbackApi.batch(targetType, targetIds);
      set((s) => {
        const updated = { ...s.feedbacks };
        for (const [id, value] of Object.entries(res.feedbacks)) {
          updated[`${targetType}:${id}`] = value;
        }
        return { feedbacks: updated };
      });
    } catch {
      /* ignore */
    }
  },
}));
