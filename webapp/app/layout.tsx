import type { ReactNode } from "react";
import "./globals.css";
import type { Metadata } from "next";
import { SiteHeader } from "@/components/site-header";

export const metadata: Metadata = {
  title: "ITA Jobs",
  description: "Agrégateur des offres des instituts techniques agricoles."
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="fr">
      <body>
        <SiteHeader />
        <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">{children}</main>
      </body>
    </html>
  );
}
