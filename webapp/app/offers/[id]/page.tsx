import Link from "next/link";
import { notFound } from "next/navigation";
import { getOfferById } from "@/lib/queries";

type Params = Promise<{ id: string }>;

function formatDate(value?: string | null, withTime = false) {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return withTime ? date.toLocaleString("fr-FR") : date.toLocaleDateString("fr-FR");
}

function Row({ label, value }: { label: string; value?: string | null }) {
  return (
    <div className="rounded-3xl border border-black/10 bg-[#f6f3ee] p-4">
      <dt className="text-xs font-black uppercase tracking-[0.18em] text-slate-500">{label}</dt>
      <dd className="mt-2 text-sm font-black text-black">{value || "n.d."}</dd>
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
      <Link href="/" className="inline-flex rounded-full bg-white px-4 py-2 text-sm font-black text-black shadow-sm ring-1 ring-black/10 hover:bg-black hover:text-white">
        ← Retour aux offres
      </Link>

      <section className="overflow-hidden rounded-[2rem] border border-black/10 bg-white shadow-sm">
        <div className="grid gap-0 lg:grid-cols-[1fr_360px]">
          <div className="p-6 sm:p-8 lg:p-10">
            <p className="inline-flex rounded-full bg-[#ffcd00] px-4 py-2 text-xs font-black uppercase tracking-[0.18em] text-black">
              {offer.source_name || offer.organization || "Institut technique agricole"}
            </p>
            <h1 className="mt-6 text-3xl font-black leading-tight tracking-tight text-black sm:text-5xl">
              {offer.title}
            </h1>
            <p className="mt-5 text-base font-semibold leading-7 text-slate-600">
              {offer.location_text || "Localisation non précisée"}
              {offer.contract_type ? ` · ${offer.contract_type}` : ""}
              {offer.offer_type ? ` · ${offer.offer_type}` : ""}
            </p>

            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <a
                href={offer.application_url ?? offer.source_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center justify-center rounded-full bg-black px-6 py-3 text-sm font-black text-white hover:bg-slate-800"
              >
                Ouvrir l&apos;annonce d&apos;origine ↗
              </a>
              <a
                href={offer.source_url}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center justify-center rounded-full border border-black px-6 py-3 text-sm font-black text-black hover:bg-black hover:text-white"
              >
                Voir la page source
              </a>
            </div>
          </div>

          <aside className="border-t border-black/10 bg-black p-6 text-white lg:border-l lg:border-t-0 lg:p-8">
            <p className="text-sm font-black uppercase tracking-[0.2em] text-white/50">Résumé</p>
            <dl className="mt-5 grid gap-3">
              <div className="rounded-3xl bg-white/10 p-4">
                <dt className="text-xs font-bold uppercase tracking-[0.16em] text-white/50">Statut</dt>
                <dd className="mt-2 text-lg font-black">{offer.archived_at ? "Archivée" : "Active"}</dd>
              </div>
              <div className="rounded-3xl bg-white/10 p-4">
                <dt className="text-xs font-bold uppercase tracking-[0.16em] text-white/50">Dernière détection</dt>
                <dd className="mt-2 text-lg font-black">{formatDate(offer.last_seen_at, true) || "n.d."}</dd>
              </div>
            </dl>
          </aside>
        </div>
      </section>

      <section className="rounded-[2rem] border border-black/10 bg-white p-5 shadow-sm sm:p-8">
        <h2 className="text-xl font-black tracking-tight text-black">Informations clés</h2>
        <dl className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <Row label="Type" value={offer.offer_type} />
          <Row label="Contrat" value={offer.contract_type} />
          <Row label="Localisation" value={offer.location_text} />
          <Row label="Télétravail" value={offer.remote_mode} />
          <Row label="Publié le" value={formatDate(offer.posted_at)} />
          <Row label="Première détection" value={formatDate(offer.first_seen_at, true)} />
          <Row label="Dernière détection" value={formatDate(offer.last_seen_at, true)} />
          <Row label="Statut" value={offer.archived_at ? "archivée" : "active"} />
        </dl>
      </section>

      <section className="rounded-[2rem] border border-black/10 bg-white p-5 shadow-sm sm:p-8">
        <h2 className="text-xl font-black tracking-tight text-black">Description</h2>
        <div className="mt-5 whitespace-pre-wrap text-sm font-medium leading-8 text-slate-700 sm:text-base">
          {offer.description_text || "Aucune description structurée disponible dans la base pour cette annonce."}
        </div>
      </section>
    </div>
  );
}
