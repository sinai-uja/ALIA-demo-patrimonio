"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { useAuthStore } from "@/store/auth";
import { auth as authApi } from "@/lib/api";
import type { ProfileType } from "@/lib/api";

const baseLinks = [
  { href: "/search", label: "Búsqueda" },
  { href: "/routes", label: "Rutas" },
];

export function NavBar() {
  const pathname = usePathname();
  const logout = useAuthStore((s) => s.logout);
  const username = useAuthStore((s) => s.username);
  const profileType = useAuthStore((s) => s.profileType);
  const setProfileType = useAuthStore((s) => s.setProfileType);
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);

  const links = [
    ...baseLinks,
    ...(profileType === "admin" ? [{ href: "/admin", label: "Admin" }] : []),
  ];

  const [profileTypes, setProfileTypes] = useState<ProfileType[]>([]);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) return;
    authApi.getProfileTypes().then(setProfileTypes).catch(() => {});
  }, [isAuthenticated]);

  // Close mobile menu on route change
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  const handleProfileChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value;
    if (value) {
      setProfileType(value);
    }
  };

  return (
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
                  <span className="px-4 text-sm text-stone-500">{username}</span>
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
  );
}
