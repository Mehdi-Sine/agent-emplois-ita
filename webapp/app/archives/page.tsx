import { OfferCard } from "@/components/offer-card";
import { getArchivedOffers } from "@/lib/queries";

export default async function ArchivesPage() {
  const offers = await getArchivedOffers();

  return (
    <div className="space-y-6">
      <section className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
        <h1 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
          Offres archivées
        </h1>
        <p className="mt-2 text-sm text-slate-600">
          Ces offres ne sont plus détectées sur les sites sources après plusieurs moissons réussies.
        </p>
      </section>

      <section className="grid gap-4">
        {offers.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
            Aucune archive pour le moment.
          </div>
        ) : (
          offers.map((offer) => <OfferCard key={offer.id} offer={offer} />)
        )}
      </section>
    </div>
  );
}
