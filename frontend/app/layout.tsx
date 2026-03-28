import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { NavBar } from "@/components/NavBar";
import { AuthHydrator } from "@/components/AuthHydrator";
import { Footer } from "@/components/Footer";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Patrimonio de Andalucía",
  description: "Asistente conversacional RAG para el patrimonio histórico andaluz",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased bg-stone-50 text-stone-900`}>
        <AuthHydrator>
          <div className="flex flex-col min-h-screen">
            <div className="h-0.5 bg-gradient-to-r from-green-600 via-emerald-600 to-teal-600" />
            <NavBar />
            <main className="flex-1">{children}</main>
            <Footer />
          </div>
        </AuthHydrator>
      </body>
    </html>
  );
}
