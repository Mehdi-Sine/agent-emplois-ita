import type { ReactNode } from "react";
import Link from "next/link";
import type { Offer } from "@/types";

function Badge({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-medium text-slate-700">
      {children}
    </span>
  );
}

export function OfferCard({ offer }: { offer: Offer }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm transition hover:-translate-y-0.5 hover:shadow-md sm:p-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-slate-500">{offer.source_name}</p>
          <h2 className="mt-1 text-lg font-semibold tracking-tight text-slate-900">
            <Link href={`/offers/${offer.id}`} className="hover:text-slate-700">
              {offer.title}
            </Link>
          </h2>
          <div className="mt-3 flex flex-wrap gap-2">
            {offer.offer_type ? <Badge>{offer.offer_type}</Badge> : null}
            {offer.contract_type ? <Badge>{offer.contract_type}</Badge> : null}
            {offer.location_text ? <Badge>{offer.location_text}</Badge> : null}
          </div>
        </div>

        <div className="flex shrink-0 flex-col gap-2 sm:items-end">
          <a
            href={offer.application_url ?? offer.source_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center rounded-xl bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800"
          >
            Voir l&apos;annonce
          </a>
          <p className="text-xs text-slate-500">
            Dernière détection : {offer.last_seen_at ? new Date(offer.last_seen_at).toLocaleString("fr-FR") : "n.d."}
          </p>
        </div>
      </div>
    </article>
  );
}
