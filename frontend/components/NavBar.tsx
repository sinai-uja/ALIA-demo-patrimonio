"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { useAuthStore } from "@/store/auth";
import { auth as authApi, health } from "@/lib/api";
import type { ProfileType, ServiceStatus } from "@/lib/api";

const baseLinks = [
  { href: "/search", label: "Búsqueda" },
  { href: "/routes", label: "Rutas" },
];

function getStatusLabel(status: string): string {
  switch (status) {
    case "ok": return "activo";
    case "warming": return "arrancando...";
    case "down": return "no disponible";
    case "local": return "local";
    case "external": return "API externa";
    default: return "desconocido";
  }
}

function getStatusColor(status: string): string {
  switch (status) {
    case "ok": return "bg-green-500";
    case "warming": return "bg-yellow-500";
    case "down": return "bg-red-500";
    case "local": return "bg-stone-300";
    case "external": return "bg-stone-300";
    default: return "bg-stone-300";
  }
}

function getOverallDotColor(s: ServiceStatus | null, isAuthenticated: boolean): string {
  if (!isAuthenticated || !s) return "bg-stone-300";
  const statuses = [s.embedding.status, s.llm.status];
  const hasCloudRun = s.embedding.is_cloud_run || s.llm.is_cloud_run;
  if (!hasCloudRun) return "bg-stone-300";
  if (statuses.includes("down")) return "bg-red-500";
  if (statuses.includes("warming")) return "bg-yellow-500";
  const allOkOrLocal = statuses.every(
    (st) => st === "ok" || st === "local" || st === "external"
  );
  if (allOkOrLocal) return "bg-green-500";
  return "bg-stone-300";
}

function relativeTime(iso: string | null): string {
  if (!iso) return "nunca";
  const diff = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (diff < 5) return "ahora";
  if (diff < 60) return `hace ${diff} seg`;
  const mins = Math.floor(diff / 60);
  if (mins < 60) return `hace ${mins} min`;
  const hours = Math.floor(mins / 60);
  return `hace ${hours} h`;
}

function StatusIndicator({
  serviceStatus,
  isAuthenticated,
}: {
  serviceStatus: ServiceStatus | null;
  isAuthenticated: boolean;
}) {
  const [showTooltip, setShowTooltip] = useState(false);
  const tooltipRef = useRef<HTMLDivElement>(null);

  if (!isAuthenticated) return null;

  const dotColor = getOverallDotColor(serviceStatus, isAuthenticated);
  const isWarming = serviceStatus
    ? serviceStatus.embedding.status === "warming" || serviceStatus.llm.status === "warming"
    : false;

  return (
    <div
      className="relative flex items-center"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <span
        className={`w-2.5 h-2.5 rounded-full ${dotColor} ${isWarming ? "animate-pulse" : ""} cursor-pointer`}
      />
      {showTooltip && serviceStatus && (
        <div
          ref={tooltipRef}
          className="absolute top-full right-1/2 translate-x-1/2 mt-2 z-50 bg-white rounded-xl shadow-lg border border-stone-200 p-3 min-w-[220px]"
        >
          <p className="text-xs font-semibold text-stone-700 mb-2">Estado de servicios</p>
          <div className="space-y-1.5">
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 text-stone-600">
                <span
                  className={`w-2 h-2 rounded-full ${getStatusColor(serviceStatus.embedding.status)} ${serviceStatus.embedding.status === "warming" ? "animate-pulse" : ""}`}
                />
                Embedding
              </span>
              <span className="text-stone-500">{getStatusLabel(serviceStatus.embedding.status)}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="flex items-center gap-1.5 text-stone-600">
                <span
                  className={`w-2 h-2 rounded-full ${getStatusColor(serviceStatus.llm.status)} ${serviceStatus.llm.status === "warming" ? "animate-pulse" : ""}`}
                />
                LLM (ALIA)
              </span>
              <span className="text-stone-500">{getStatusLabel(serviceStatus.llm.status)}</span>
            </div>
          </div>
          <div className="mt-2 pt-2 border-t border-stone-100 space-y-0.5">
            <p className="text-[11px] text-stone-400">
              Proveedor: <span className="text-stone-500">{serviceStatus.provider}</span>
            </p>
            <p className="text-[11px] text-stone-400">
              Último check: <span className="text-stone-500">{relativeTime(serviceStatus.last_check)}</span>
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export function NavBar() {
  const pathname = usePathname();
  const logout = useAuthStore((s) => s.logout);
  const username = useAuthStore((s) => s.username);
  const profileType = useAuthStore((s) => s.profileType);
  const setProfileType = useAuthStore((s) => s.setProfileType);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const hydrated = useAuthStore((s) => s.hydrated);

  const links = [
    ...baseLinks,
    ...(profileType === "admin" ? [{ href: "/admin", label: "Admin" }] : []),
  ];

  const [profileTypes, setProfileTypes] = useState<ProfileType[]>([]);
  const [menuOpen, setMenuOpen] = useState(false);
  const [serviceStatus, setServiceStatus] = useState<ServiceStatus | null>(null);
  const [showToast, setShowToast] = useState(false);
  const prevStatusRef = useRef<string>("unknown");

  useEffect(() => {
    if (!isAuthenticated) return;
    authApi.getProfileTypes().then(setProfileTypes).catch(() => {});
  }, [isAuthenticated]);

  // Close mobile menu on route change
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  // Health status polling + keepalive
  useEffect(() => {
    if (!isAuthenticated || !hydrated) return;

    const fetchStatus = async () => {
      try {
        const s = await health.status();
        const allOk =
          (s.embedding.status === "ok" || !s.embedding.is_cloud_run) &&
          (s.llm.status === "ok" || !s.llm.is_cloud_run || s.provider === "gemini");
        if (allOk && prevStatusRef.current === "not_ok") {
          setShowToast(true);
          setTimeout(() => setShowToast(false), 3000);
        }
        prevStatusRef.current = allOk ? "ok" : "not_ok";
        setServiceStatus(s);
      } catch (err) {
        console.warn("[health status] failed:", err);
      }
    };

    const doKeepalive = async () => {
      try {
        const s = await health.keepalive();
        setServiceStatus(s);
      } catch (err) {
        console.warn("[keepalive] failed:", err);
      }
    };

    fetchStatus();
    doKeepalive();
    const statusInterval = setInterval(fetchStatus, 10_000);
    const keepaliveInterval = setInterval(doKeepalive, 3 * 60 * 1000);

    return () => {
      clearInterval(statusInterval);
      clearInterval(keepaliveInterval);
    };
  }, [isAuthenticated, hydrated]);

  const handleProfileChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    if (value) {
      setProfileType(value);
    }
  };

  return (
    <>
      <header className="sticky top-0 z-50 border-b border-stone-200/60 bg-white/80 backdrop-blur-lg">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
          {/* Left: logo */}
          <Link href="/" className="flex items-center gap-2.5 group">
            <img src="/images/alia-navbar.png" alt="ALIA" className="h-7 w-auto" />
            <span className="font-semibold text-stone-800 group-hover:text-green-700 transition-colors">
              Patrimonio de Andalucía
            </span>
          </Link>

          {/* Center: nav links (desktop only) */}
          <nav className="hidden md:flex absolute left-1/2 -translate-x-1/2 items-center gap-1">
            {links.map((l) => {
              const active = pathname.startsWith(l.href);
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  className={`rounded-lg px-4 py-1.5 text-sm font-medium transition-all ${
                    active
                      ? "bg-green-50 text-green-800"
                      : "text-stone-500 hover:text-stone-800 hover:bg-stone-100"
                  }`}
                >
                  {l.label}
                </Link>
              );
            })}
          </nav>

          {/* Right: profile + logout (desktop only) */}
          <div className="hidden md:flex items-center gap-3">
            {isAuthenticated && username && (
              <>
                <span className="text-sm text-stone-500">{username}</span>
                <StatusIndicator serviceStatus={serviceStatus} isAuthenticated={isAuthenticated} />
                {profileType === "admin" ? (
                  <span className="rounded-full border border-red-200 bg-red-50 px-3 py-1 text-xs font-semibold text-red-700 capitalize select-none">
                    admin
                  </span>
                ) : profileTypes.length > 0 ? (
                  <div className="relative">
                    <select
                      value={profileType ?? ""}
                      onChange={handleProfileChange}
                      className="appearance-none rounded-full border border-stone-200 bg-stone-50 pl-3 pr-7 py-1 text-xs font-medium text-stone-600 shadow-sm outline-none hover:bg-white hover:border-stone-300 focus:border-green-500 focus:ring-2 focus:ring-green-500/20 transition-all cursor-pointer capitalize"
                    >
                      <option value="" disabled>
                        Perfil
                      </option>
                      {profileTypes.map((pt) => (
                        <option key={pt.name} value={pt.name} className="capitalize">
                          {pt.name}
                        </option>
                      ))}
                    </select>
                    <svg
                      className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-stone-400"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2.5}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                    </svg>
                  </div>
                ) : null}
              </>
            )}
            <div className="h-4 w-px bg-stone-200" />
            <button
              onClick={logout}
              className="rounded-lg px-3 py-1.5 text-sm font-medium text-stone-500 hover:text-red-600 hover:bg-red-50 transition-all"
            >
              Cerrar sesión
            </button>
          </div>

          {/* Hamburger button (mobile only) */}
          <button
            onClick={() => setMenuOpen((prev) => !prev)}
            className="md:hidden flex items-center justify-center rounded-lg p-2 text-stone-500 hover:bg-stone-100 hover:text-stone-800 transition-all"
            aria-label="Abrir menú"
            aria-expanded={menuOpen}
          >
            {menuOpen ? (
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            )}
          </button>
        </div>

        {/* Mobile menu panel */}
        {menuOpen && (
          <div className="md:hidden absolute left-0 right-0 border-b border-stone-200 bg-white shadow-lg">
            <div className="mx-auto max-w-6xl px-6 py-4 space-y-4">
              {/* Nav links */}
              <nav className="flex flex-col gap-1">
                {links.map((l) => {
                  const active = pathname.startsWith(l.href);
                  return (
                    <Link
                      key={l.href}
                      href={l.href}
                      className={`rounded-lg px-4 py-2 text-sm font-medium transition-all ${
                        active
                          ? "bg-green-50 text-green-800"
                          : "text-stone-500 hover:text-stone-800 hover:bg-stone-100"
                      }`}
                    >
                      {l.label}
                    </Link>
                  );
                })}
              </nav>

              {/* Divider */}
              <div className="h-px bg-stone-200" />

              {/* Profile + logout */}
              <div className="flex flex-col gap-3">
                {isAuthenticated && username && (
                  <>
                    <div className="flex items-center gap-2 px-4">
                      <span className="text-sm text-stone-500">{username}</span>
                      <StatusIndicator serviceStatus={serviceStatus} isAuthenticated={isAuthenticated} />
                    </div>
                    {profileType === "admin" ? (
                      <span className="mx-4 rounded-full border border-red-200 bg-red-50 px-3 py-1 text-xs font-semibold text-red-700 capitalize select-none">
                        admin
                      </span>
                    ) : profileTypes.length > 0 ? (
                      <div className="relative px-4">
                        <select
                          value={profileType ?? ""}
                          onChange={handleProfileChange}
                          className="w-full appearance-none rounded-full border border-stone-200 bg-stone-50 pl-3 pr-7 py-1.5 text-xs font-medium text-stone-600 shadow-sm outline-none hover:bg-white hover:border-stone-300 focus:border-green-500 focus:ring-2 focus:ring-green-500/20 transition-all cursor-pointer capitalize"
                        >
                          <option value="" disabled>
                            Perfil
                          </option>
                          {profileTypes.map((pt) => (
                            <option key={pt.name} value={pt.name} className="capitalize">
                              {pt.name}
                            </option>
                          ))}
                        </select>
                        <svg
                          className="pointer-events-none absolute right-6 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-stone-400"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                          strokeWidth={2.5}
                        >
                          <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                        </svg>
                      </div>
                    ) : null}
                  </>
                )}
                <button
                  onClick={logout}
                  className="rounded-lg px-4 py-2 text-left text-sm font-medium text-stone-500 hover:text-red-600 hover:bg-red-50 transition-all"
                >
                  Cerrar sesión
                </button>
              </div>
            </div>
          </div>
        )}
      </header>

      {/* Toast: Servicios listos */}
      {showToast && (
        <div className="fixed bottom-4 right-4 z-50 bg-green-600 text-white rounded-lg px-4 py-2.5 shadow-lg text-sm animate-fade-in flex items-center gap-2">
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
          Servicios listos
        </div>
      )}
    </>
  );
}
