import type { ReactNode } from "react";
import Link from "next/link";
import type { Offer } from "@/types";

function Badge({ children, accent = false }: { children: ReactNode; accent?: boolean }) {
  return (
    <span
      className={
        accent
          ? "inline-flex rounded-full bg-[#ffcd00] px-3 py-1 text-xs font-black uppercase tracking-wide text-black"
          : "inline-flex rounded-full border border-black/10 bg-white px-3 py-1 text-xs font-bold text-slate-700"
      }
    >
      {children}
    </span>
  );
}

function formatDate(value?: string | null) {
  if (!value) return "n.d.";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "n.d.";
  return date.toLocaleDateString("fr-FR", { day: "2-digit", month: "short", year: "numeric" });
}

export function OfferCard({ offer }: { offer: Offer }) {
  const href = offer.application_url ?? offer.source_url;

  return (
    <article className="group rounded-[1.75rem] border border-black/10 bg-white p-4 shadow-sm transition duration-200 hover:-translate-y-0.5 hover:border-black hover:shadow-xl sm:p-5">
      <div className="flex flex-col gap-5 lg:flex-row lg:items-center lg:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Badge accent>{offer.source_name || offer.organization || "ITA"}</Badge>
            {offer.offer_type ? <Badge>{offer.offer_type}</Badge> : null}
            {offer.contract_type ? <Badge>{offer.contract_type}</Badge> : null}
          </div>

          <h2 className="mt-4 text-xl font-black leading-tight tracking-tight text-black sm:text-2xl">
            <Link href={`/offers/${offer.id}`} className="hover:underline hover:decoration-2 hover:underline-offset-4">
              {offer.title}
            </Link>
          </h2>

          <div className="mt-4 grid gap-2 text-sm font-medium text-slate-600 sm:grid-cols-3">
            <p className="truncate">📍 {offer.location_text || "Lieu non précisé"}</p>
            <p>🗓 Dernière détection : {formatDate(offer.last_seen_at)}</p>
            <p>{offer.remote_mode ? `💻 ${offer.remote_mode}` : "🌾 Institut technique agricole"}</p>
          </div>
        </div>

        <div className="flex shrink-0 flex-col gap-2 sm:flex-row lg:flex-col lg:items-stretch">
          <Link
            href={`/offers/${offer.id}`}
            className="inline-flex items-center justify-center rounded-full border border-black px-5 py-3 text-sm font-black text-black hover:bg-black hover:text-white"
          >
            Détail
          </Link>
          <a
            href={href}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center rounded-full bg-black px-5 py-3 text-sm font-black text-white hover:bg-slate-800"
          >
            Postuler ↗
          </a>
        </div>
      </div>
    </article>
  );
}
