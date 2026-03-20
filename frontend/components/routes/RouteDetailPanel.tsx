"use client";

import { useRoutesStore } from "@/store/routes";
import { AssetDetailContent } from "@/components/shared/AssetDetailContent";

export function RouteDetailPanel() {
  const selectedAsset = useRoutesStore((s) => s.selectedAsset);
  const detailLoading = useRoutesStore((s) => s.detailLoading);
  const closeStopDetail = useRoutesStore((s) => s.closeStopDetail);

  if (!selectedAsset && !detailLoading) return null;

  return (
    <AssetDetailContent
      asset={selectedAsset!}
      onClose={closeStopDetail}
      loading={detailLoading}
    />
  );
}
