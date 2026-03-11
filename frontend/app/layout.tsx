import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import Link from "next/link";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "IAPH · Asistente Patrimonio",
  description: "Asistente conversacional RAG para el patrimonio histórico andaluz",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased bg-stone-50 text-gray-900`}>
        <header className="sticky top-0 z-50 border-b border-amber-100 bg-white/80 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center gap-6 px-4 py-3">
            <Link href="/" className="flex items-center gap-2">
              <span className="text-xl">🏛️</span>
              <span className="font-semibold text-amber-800">IAPH Heritage</span>
            </Link>
            <nav className="flex gap-4 text-sm text-gray-600">
              <Link href="/chat" className="hover:text-amber-700 transition-colors">Chatbot</Link>
              <Link href="/routes" className="hover:text-amber-700 transition-colors">Rutas Virtuales</Link>
              <Link href="/accessibility" className="hover:text-amber-700 transition-colors">Lectura Fácil</Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
      </body>
    </html>
  );
}
