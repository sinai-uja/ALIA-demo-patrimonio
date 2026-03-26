"use client";

import { useState } from "react";
import type { ImageInfo } from "@/lib/api";

function buildImageUrl(assetId: string, imageId: string): string {
  return `https://guiadigital.iaph.es/imagenes-cache/${assetId}/${imageId}--fic.jpg`;
}

export function AssetImageGallery({
  images,
  assetId,
}: {
  images: ImageInfo[];
  assetId: string;
}) {
  const [active, setActive] = useState(0);
  const [broken, setBroken] = useState<Set<number>>(new Set());

  const validImages = images.filter(
    (img, i) => img.id && !broken.has(i),
  );

  if (validImages.length === 0) return null;

  const current = validImages[active >= validImages.length ? 0 : active];
  const currentIdx = active >= validImages.length ? 0 : active;

  return (
    <div className="space-y-2">
      {/* Main image */}
      <div className="relative w-full aspect-[4/3] rounded-xl overflow-hidden bg-stone-100">
        <img
          src={buildImageUrl(assetId, current.id!)}
          alt={current.title ?? "Imagen del activo"}
          className="w-full h-full object-cover"
          onError={() => {
            const origIdx = images.indexOf(current);
            if (origIdx >= 0) {
              setBroken((prev) => new Set(prev).add(origIdx));
            }
          }}
        />
        {/* Navigation arrows */}
        {validImages.length > 1 && (
          <>
            <button
              onClick={() => setActive((i) => (i - 1 + validImages.length) % validImages.length)}
              className="absolute left-2 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-black/40 text-white flex items-center justify-center hover:bg-black/60 transition-colors"
              aria-label="Imagen anterior"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
              </svg>
            </button>
            <button
              onClick={() => setActive((i) => (i + 1) % validImages.length)}
              className="absolute right-2 top-1/2 -translate-y-1/2 w-7 h-7 rounded-full bg-black/40 text-white flex items-center justify-center hover:bg-black/60 transition-colors"
              aria-label="Imagen siguiente"
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
              </svg>
            </button>
            <span className="absolute bottom-2 right-2 px-2 py-0.5 rounded-full bg-black/40 text-white text-[10px] font-medium">
              {currentIdx + 1}/{validImages.length}
            </span>
          </>
        )}
      </div>

      {/* Caption */}
      {(current.title || current.author || current.date) && (
        <div className="text-xs text-stone-500 space-y-0.5 px-1">
          {current.title && <p className="font-medium text-stone-600">{current.title}</p>}
          {current.author && <p>{current.author}</p>}
          {current.date && <p className="text-stone-400">{current.date}</p>}
        </div>
      )}

      {/* Thumbnails */}
      {validImages.length > 1 && (
        <div className="flex gap-1.5 overflow-x-auto pb-1">
          {validImages.map((img, i) => (
            <button
              key={img.id}
              onClick={() => setActive(i)}
              className={`shrink-0 w-14 h-14 rounded-lg overflow-hidden border-2 transition-colors ${
                i === currentIdx ? "border-green-600" : "border-transparent hover:border-stone-300"
              }`}
            >
              <img
                src={buildImageUrl(assetId, img.id!)}
                alt={img.title ?? `Imagen ${i + 1}`}
                className="w-full h-full object-cover"
                loading="lazy"
                onError={() => {
                  const origIdx = images.indexOf(img);
                  if (origIdx >= 0) {
                    setBroken((prev) => new Set(prev).add(origIdx));
                  }
                }}
              />
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
