"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/chat", label: "Chat" },
  { href: "/search", label: "Busqueda" },
  { href: "/routes", label: "Rutas" },
  { href: "/accessibility", label: "Accesibilidad" },
];

export function NavBar() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 border-b border-stone-200/60 bg-white/80 backdrop-blur-lg">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <Link href="/" className="flex items-center gap-2.5 group">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-amber-500 to-orange-600 text-white text-sm font-bold shadow-sm">
            IA
          </div>
          <span className="font-semibold text-stone-800 group-hover:text-amber-700 transition-colors">
            IAPH Heritage
          </span>
        </Link>
        <nav className="flex items-center gap-1">
          {links.map((l) => {
            const active = pathname.startsWith(l.href);
            return (
              <Link
                key={l.href}
                href={l.href}
                className={`rounded-lg px-3.5 py-1.5 text-sm font-medium transition-all ${
                  active
                    ? "bg-amber-50 text-amber-800"
                    : "text-stone-500 hover:text-stone-800 hover:bg-stone-100"
                }`}
              >
                {l.label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
