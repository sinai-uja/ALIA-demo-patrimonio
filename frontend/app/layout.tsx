import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { NavBar } from "@/components/NavBar";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "IAPH · Asistente Patrimonio",
  description: "Asistente conversacional RAG para el patrimonio histórico andaluz",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased bg-stone-50 text-stone-900`}>
        <div className="h-0.5 bg-gradient-to-r from-green-600 via-emerald-600 to-teal-600" />
        <NavBar />
        <main>{children}</main>
      </body>
    </html>
  );
}
