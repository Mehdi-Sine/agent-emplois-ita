import Link from "next/link";
import { notFound } from "next/navigation";
import { getOfferById } from "@/lib/queries";

type Params = Promise<{ id: string }>;

function Row({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4">
      <dt className="text-sm text-slate-500">{label}</dt>
      <dd className="mt-1 text-sm font-medium text-slate-900">{value || "n.d."}</dd>
    </div>
  );
}

export default async function OfferDetailPage(props: { params: Params }) {
  const params = await props.params;
  const offer = await getOfferById(params.id);

  if (!offer) {
    notFound();
  }

  return (
    <div className="space-y-6">
      <Link href="/" className="inline-flex text-sm font-medium text-slate-700 underline underline-offset-2">
        ← Retour aux offres
      </Link>

      <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
        <p className="text-sm font-medium text-slate-500">{offer.source_name}</p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-slate-900 sm:text-4xl">
          {offer.title}
        </h1>

        <div className="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Row label="Type" value={offer.offer_type} />
          <Row label="Contrat" value={offer.contract_type} />
          <Row label="Localisation" value={offer.location_text} />
          <Row label="Télétravail" value={offer.remote_mode} />
          <Row label="Publié le" value={offer.posted_at ? new Date(offer.posted_at).toLocaleDateString("fr-FR") : null} />
          <Row label="Première détection" value={offer.first_seen_at ? new Date(offer.first_seen_at).toLocaleString("fr-FR") : null} />
          <Row label="Dernière détection" value={offer.last_seen_at ? new Date(offer.last_seen_at).toLocaleString("fr-FR") : null} />
          <Row label="Statut" value={offer.archived_at ? "archivée" : "active"} />
        </div>

        <div className="mt-6 flex flex-col gap-3 sm:flex-row">
          <a
            href={offer.application_url ?? offer.source_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center rounded-2xl bg-slate-900 px-5 py-3 text-sm font-medium text-white hover:bg-slate-800"
          >
            Ouvrir l&apos;annonce d&apos;origine
          </a>
          <a
            href={offer.source_url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center justify-center rounded-2xl border border-slate-300 px-5 py-3 text-sm font-medium text-slate-900 hover:bg-slate-50"
          >
            Voir la page source
          </a>
        </div>
      </section>

      <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-8">
        <h2 className="text-lg font-semibold text-slate-900">Description</h2>
        <div className="mt-4 whitespace-pre-wrap text-sm leading-7 text-slate-700 sm:text-base">
          {offer.description_text || "Aucune description structurée disponible dans la base pour cette annonce."}
        </div>
      </section>
    </div>
  );
}
