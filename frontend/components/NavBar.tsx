"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuthStore } from "@/store/auth";

const links = [
  { href: "/search", label: "Busqueda" },
  { href: "/routes", label: "Rutas" },
];

export function NavBar() {
  const pathname = usePathname();
  const logout = useAuthStore((s) => s.logout);

  return (
    <header className="sticky top-0 z-50 border-b border-stone-200/60 bg-white/80 backdrop-blur-lg">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-green-600 to-emerald-700 text-white text-sm font-bold shadow-sm">
            PA
          </div>
          <span className="font-semibold text-stone-800 group-hover:text-green-700 transition-colors">
            IAPH Heritage
          </span>
        </Link>
        <div className="flex items-center gap-1">
          <nav className="flex items-center gap-1">
            {links.map((l) => {
              const active = pathname.startsWith(l.href);
              return (
                <Link
                  key={l.href}
                  href={l.href}
                  className={`rounded-lg px-3.5 py-1.5 text-sm font-medium transition-all ${
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
          <button
            onClick={logout}
            className="ml-4 rounded-lg px-3.5 py-1.5 text-sm font-medium text-stone-500 hover:text-red-600 hover:bg-red-50 transition-all"
          >
            Cerrar sesión
          </button>
        </div>
      </div>
    </header>
  );
}
