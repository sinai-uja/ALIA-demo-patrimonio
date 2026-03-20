"use client";

import dynamic from "next/dynamic";
import { AssetImageGallery } from "@/components/search/AssetImageGallery";
import type {
  HeritageAsset,
  HeritageDetails,
  InmuebleDetails,
  MuebleDetails,
  InmaterialDetails,
  PaisajeDetails,
  TypologyInfo,
  BibliographyEntry,
  RelatedAsset,
} from "@/lib/api";

const AssetLocationMap = dynamic(
  () => import("@/components/search/AssetLocationMap"),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-48 rounded-xl bg-stone-100 animate-pulse" />
    ),
  },
);

export const HERITAGE_LABELS: Record<string, string> = {
  inmueble: "Patrimonio Inmueble",
  mueble: "Patrimonio Mueble",
  inmaterial: "Patrimonio Inmaterial",
  paisaje: "Paisaje Cultural",
  patrimonio_inmueble: "Patrimonio Inmueble",
  patrimonio_mueble: "Patrimonio Mueble",
  patrimonio_inmaterial: "Patrimonio Inmaterial",
  paisaje_cultural: "Paisaje Cultural",
};

export const HERITAGE_COLORS: Record<string, string> = {
  inmueble: "bg-amber-100 text-amber-800",
  mueble: "bg-violet-100 text-violet-800",
  inmaterial: "bg-emerald-100 text-emerald-800",
  paisaje: "bg-sky-100 text-sky-800",
  patrimonio_inmueble: "bg-amber-100 text-amber-800",
  patrimonio_mueble: "bg-violet-100 text-violet-800",
  patrimonio_inmaterial: "bg-emerald-100 text-emerald-800",
  paisaje_cultural: "bg-sky-100 text-sky-800",
};

function hasValue(v: string | null | undefined): v is string {
  return v != null && v.trim().length > 0;
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-2">
      <h4 className="text-xs font-semibold text-stone-400 uppercase tracking-wide">
        {title}
      </h4>
      <div className="space-y-1.5">{children}</div>
    </div>
  );
}

function Field({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  if (!hasValue(value)) return null;
  return (
    <p className="text-sm text-stone-700">
      <span className="font-semibold text-stone-800">{label}: </span>
      {value.trim()}
    </p>
  );
}

function LongField({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  if (!hasValue(value)) return null;
  return (
    <div>
      <p className="text-xs text-stone-600 leading-relaxed whitespace-pre-line max-h-60 overflow-y-auto">
        <span className="font-semibold text-stone-800">{label}: </span>
        {value.trim()}
      </p>
    </div>
  );
}

function Tags({ items }: { items: string[] }) {
  if (items.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1.5">
      {items.map((item, i) => (
        <span
          key={i}
          className="px-2 py-0.5 rounded-full bg-stone-100 text-stone-600 text-xs"
        >
          {item}
        </span>
      ))}
    </div>
  );
}

function TypologiesTable({ typologies }: { typologies: TypologyInfo[] }) {
  const valid = typologies.filter(
    (t) => hasValue(t.typology) || hasValue(t.style) || hasValue(t.period),
  );
  if (valid.length === 0) return null;
  return (
    <Section title="Tipologias">
      <div className="space-y-1.5">
        {valid.map((t, i) => (
          <div
            key={i}
            className="text-xs text-stone-600 border-l-2 border-stone-200 pl-2"
          >
            {hasValue(t.typology) && (
              <p className="font-medium text-stone-700">{t.typology}</p>
            )}
            {hasValue(t.style) && <p>Estilo: {t.style}</p>}
            {hasValue(t.period) && <p>Periodo: {t.period}</p>}
            {(hasValue(t.chrono_start) || hasValue(t.chrono_end)) && (
              <p className="text-stone-400">
                {t.chrono_start ?? "?"} — {t.chrono_end ?? "?"}
              </p>
            )}
          </div>
        ))}
      </div>
    </Section>
  );
}

function BibliographyList({ entries }: { entries: BibliographyEntry[] }) {
  const valid = entries.filter(
    (b) => hasValue(b.title) || hasValue(b.author),
  );
  if (valid.length === 0) return null;
  return (
    <Section title="Bibliografia">
      <ul className="space-y-2">
        {valid.map((b, i) => (
          <li
            key={i}
            className="text-xs text-stone-600 border-l-2 border-stone-200 pl-2"
          >
            {hasValue(b.author) && (
              <span className="font-medium">{b.author} </span>
            )}
            {hasValue(b.title) && <span className="italic">{b.title}</span>}
            {hasValue(b.publisher) && <span>. {b.publisher}</span>}
            {hasValue(b.year) && <span>, {b.year}</span>}
            {hasValue(b.isbn) && <span>. {b.isbn}</span>}
          </li>
        ))}
      </ul>
    </Section>
  );
}

function RelatedAssetsList({ assets }: { assets: RelatedAsset[] }) {
  const valid = assets.filter((a) => hasValue(a.denomination));
  if (valid.length === 0) return null;
  return (
    <Section title="Bienes relacionados">
      <ul className="space-y-1">
        {valid.map((a, i) => (
          <li
            key={i}
            className="text-xs text-stone-600 flex items-start gap-2"
          >
            <span className="text-stone-700">{a.denomination}</span>
            {hasValue(a.relation_type) && (
              <span className="shrink-0 px-1.5 py-0.5 rounded bg-stone-100 text-stone-400 text-[10px]">
                {a.relation_type}
              </span>
            )}
          </li>
        ))}
      </ul>
    </Section>
  );
}

function InmuebleContent({
  d,
  mapSlot,
}: {
  d: InmuebleDetails;
  mapSlot: React.ReactNode;
}) {
  const hasGeneral =
    hasValue(d.code) ||
    hasValue(d.other_denominations) ||
    hasValue(d.characterisation) ||
    hasValue(d.postal_address);
  const hasDesc = hasValue(d.description) || hasValue(d.historical_data);

  return (
    <>
      {hasGeneral && (
        <Section title="Informacion general">
          <Field label="Codigo" value={d.code} />
          <Field label="Otras denominaciones" value={d.other_denominations} />
          <Field label="Caracterizacion" value={d.characterisation} />
          <Field label="Direccion postal" value={d.postal_address} />
        </Section>
      )}
      {mapSlot}
      {hasDesc && (
        <Section title="Descripcion">
          <LongField label="Descripcion" value={d.description} />
          <LongField label="Datos historicos" value={d.historical_data} />
        </Section>
      )}
      {d.historical_periods.length > 0 && (
        <Section title="Periodos historicos">
          <Tags items={d.historical_periods} />
        </Section>
      )}
    </>
  );
}

function MuebleContent({
  d,
  mapSlot,
}: {
  d: MuebleDetails;
  mapSlot: React.ReactNode;
}) {
  const hasGeneral =
    hasValue(d.code) ||
    hasValue(d.other_denominations) ||
    hasValue(d.characterisation) ||
    hasValue(d.measurements) ||
    hasValue(d.chronology);

  return (
    <>
      {hasGeneral && (
        <Section title="Informacion general">
          <Field label="Codigo" value={d.code} />
          <Field label="Otras denominaciones" value={d.other_denominations} />
          <Field label="Caracterizacion" value={d.characterisation} />
          <Field label="Medidas" value={d.measurements} />
          <Field label="Cronologia" value={d.chronology} />
        </Section>
      )}
      {mapSlot}
      {hasValue(d.description) && (
        <Section title="Descripcion">
          <LongField label="Descripcion" value={d.description} />
        </Section>
      )}
    </>
  );
}

function InmaterialContent({
  d,
  mapSlot,
}: {
  d: InmaterialDetails;
  mapSlot: React.ReactNode;
}) {
  const hasGeneral =
    hasValue(d.code) ||
    hasValue(d.other_denominations) ||
    hasValue(d.scope) ||
    hasValue(d.framework_activities) ||
    hasValue(d.activity_dates) ||
    hasValue(d.periodicity) ||
    hasValue(d.typologies_text) ||
    hasValue(d.district) ||
    hasValue(d.local_entity);
  const hasDesc =
    hasValue(d.description) ||
    hasValue(d.development) ||
    hasValue(d.spatial_description) ||
    hasValue(d.origins) ||
    hasValue(d.evolution);
  const hasPractice =
    hasValue(d.preparations) ||
    hasValue(d.clothing) ||
    hasValue(d.instruments);
  const hasAgents =
    hasValue(d.agents_description) ||
    hasValue(d.transmission_mode) ||
    hasValue(d.transformations);

  return (
    <>
      {hasGeneral && (
        <Section title="Informacion general">
          <Field label="Codigo" value={d.code} />
          <Field label="Otras denominaciones" value={d.other_denominations} />
          <Field label="Ambito" value={d.scope} />
          <Field label="Actividades marco" value={d.framework_activities} />
          <Field label="Fechas" value={d.activity_dates} />
          <Field label="Periodicidad" value={d.periodicity} />
          <Field label="Tipologias" value={d.typologies_text} />
          <Field label="Comarca" value={d.district} />
          <Field label="Entidad local" value={d.local_entity} />
        </Section>
      )}
      {mapSlot}
      {hasDesc && (
        <Section title="Descripcion">
          <LongField label="Descripcion" value={d.description} />
          <LongField label="Desarrollo" value={d.development} />
          <LongField label="Espacio" value={d.spatial_description} />
          <LongField label="Origenes" value={d.origins} />
          <LongField label="Evolucion" value={d.evolution} />
        </Section>
      )}
      {hasPractice && (
        <Section title="Practica y elementos">
          <LongField label="Preparativos" value={d.preparations} />
          <LongField label="Indumentaria" value={d.clothing} />
          <LongField label="Instrumentos" value={d.instruments} />
        </Section>
      )}
      {hasAgents && (
        <Section title="Agentes y transmision">
          <LongField label="Agentes" value={d.agents_description} />
          <LongField label="Modo de transmision" value={d.transmission_mode} />
          <LongField label="Transformaciones" value={d.transformations} />
        </Section>
      )}
    </>
  );
}

function PaisajeContent({
  d,
  mapSlot,
}: {
  d: PaisajeDetails;
  mapSlot: React.ReactNode;
}) {
  return (
    <>
      {mapSlot}
      {hasValue(d.pdf_url) && (
        <Section title="Documento">
          <a
            href={d.pdf_url!}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs text-amber-700 hover:text-amber-800 font-medium"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              viewBox="0 0 24 24"
              strokeWidth={1.5}
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
              />
            </svg>
            Ver PDF completo
          </a>
        </Section>
      )}
      {d.search_terms.length > 0 && (
        <Section title="Terminos de busqueda">
          <Tags items={d.search_terms} />
        </Section>
      )}
    </>
  );
}

function DetailContent({
  details,
  mapSlot,
}: {
  details: HeritageDetails;
  mapSlot: React.ReactNode;
}) {
  switch (details.type) {
    case "inmueble":
      return <InmuebleContent d={details} mapSlot={mapSlot} />;
    case "mueble":
      return <MuebleContent d={details} mapSlot={mapSlot} />;
    case "inmaterial":
      return <InmaterialContent d={details} mapSlot={mapSlot} />;
    case "paisaje":
      return <PaisajeContent d={details} mapSlot={mapSlot} />;
  }
}

function SharedSections({ details }: { details: HeritageDetails }) {
  if (details.type === "paisaje") return null;
  return (
    <>
      <TypologiesTable typologies={details.typologies} />
      <BibliographyList entries={details.bibliography} />
      <RelatedAssetsList assets={details.related_assets} />
    </>
  );
}

interface AssetDetailContentProps {
  asset: HeritageAsset | null;
  onClose: () => void;
  loading: boolean;
}

export function AssetDetailContent({
  asset,
  onClose,
  loading,
}: AssetDetailContentProps) {
  return (
    <aside className="h-full border-l border-stone-200/60 bg-white flex flex-col">
      {/* Header */}
      <div className="shrink-0 flex items-start gap-3 p-4 border-b border-stone-100">
        <button
          onClick={onClose}
          className="shrink-0 w-7 h-7 rounded-full hover:bg-stone-100 flex items-center justify-center text-stone-400 hover:text-stone-600 transition-colors"
          aria-label="Cerrar panel"
        >
          <svg
            className="w-4 h-4"
            fill="none"
            viewBox="0 0 24 24"
            strokeWidth={2}
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M6 18 18 6M6 6l12 12"
            />
          </svg>
        </button>
        <div className="flex-1 min-w-0">
          {asset ? (
            <>
              <div className="flex items-center gap-2 mb-1">
                <span
                  className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${
                    HERITAGE_COLORS[asset.heritage_type] ??
                    "bg-stone-100 text-stone-700"
                  }`}
                >
                  {HERITAGE_LABELS[asset.heritage_type] ?? asset.heritage_type}
                </span>
                {asset.protection && asset.protection.toUpperCase() !== "NO" && (
                  <span className="rounded-full px-2 py-0.5 text-[10px] font-medium bg-rose-50 text-rose-700">
                    Protegido
                  </span>
                )}
              </div>
              <h3 className="font-semibold text-stone-900 text-sm leading-snug">
                {asset.denomination ?? asset.id}
              </h3>
              {(asset.province || asset.municipality) && (
                <p className="text-xs text-stone-400 mt-0.5">
                  {[asset.municipality, asset.province].filter(Boolean).join(", ")}
                </p>
              )}
            </>
          ) : (
            <p className="text-sm text-stone-400">Cargando detalle...</p>
          )}
        </div>
      </div>

      {/* Body */}
      {loading && (
        <div className="flex-1 flex items-center justify-center">
          <svg
            className="w-6 h-6 animate-spin text-amber-500"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
            />
          </svg>
        </div>
      )}

      {!loading && asset && (
        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          {/* Image gallery */}
          {asset.details &&
            asset.details.type !== "paisaje" &&
            asset.details.images.length > 0 && (
              <AssetImageGallery
                images={asset.details.images}
                assetId={asset.id}
              />
            )}

          {/* Type-specific content (map inserted after general info) */}
          {asset.details && (
            <DetailContent
              details={asset.details}
              mapSlot={
                <AssetLocationMap
                  latitude={asset.latitude}
                  longitude={asset.longitude}
                  province={asset.province}
                  municipality={asset.municipality}
                />
              }
            />
          )}

          {/* Shared sections (typologies, bibliography, related assets) */}
          {asset.details && <SharedSections details={asset.details} />}

          {/* External link */}
          <div className="pt-2 border-t border-stone-100">
            <a
              href={`https://guiadigital.iaph.es/bien/${asset.heritage_type}/${asset.id}`}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-amber-700 hover:text-amber-800 font-medium"
            >
              <svg
                className="w-3.5 h-3.5"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth={1.5}
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M13.5 6H5.25A2.25 2.25 0 0 0 3 8.25v10.5A2.25 2.25 0 0 0 5.25 21h10.5A2.25 2.25 0 0 0 18 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25"
                />
              </svg>
              Ver ficha completa en IAPH
            </a>
          </div>
        </div>
      )}
    </aside>
  );
}
