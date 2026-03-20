"use client";

import { useSearchStore } from "@/store/search";
import { AssetDetailContent } from "@/components/shared/AssetDetailContent";

export function AssetDetailPanel() {
  const asset = useSearchStore((s) => s.selectedAsset);
  const loading = useSearchStore((s) => s.detailLoading);
  const closeDetail = useSearchStore((s) => s.closeDetail);

  if (!asset && !loading) return null;

  return (
    <AssetDetailContent
      asset={asset!}
      onClose={closeDetail}
      loading={loading}
    />
  );
}
