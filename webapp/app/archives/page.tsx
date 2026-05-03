import { OfferCard } from "@/components/offer-card";
import { getArchivedOffers } from "@/lib/queries";

export default async function ArchivesPage() {
  const offers = await getArchivedOffers();

  return (
    <div className="space-y-6">
      <section className="rounded-[2rem] border border-black/10 bg-white p-6 shadow-sm sm:p-8">
        <p className="inline-flex rounded-full bg-black px-4 py-2 text-xs font-black uppercase tracking-[0.2em] text-white">
          Historique
        </p>
        <h1 className="mt-5 text-3xl font-black tracking-tight text-black sm:text-5xl">Offres archivées</h1>
        <p className="mt-4 max-w-3xl text-base font-medium leading-7 text-slate-600">
          Ces offres ne sont plus détectées sur les sites sources après plusieurs moissons réussies,
          ou ont été signalées comme closes ou pourvues par le connecteur concerné.
        </p>
      </section>

      <section className="grid gap-4">
        {offers.length === 0 ? (
          <div className="rounded-[2rem] border border-dashed border-black/20 bg-white p-10 text-center">
            <p className="text-lg font-black text-black">Aucune archive pour le moment.</p>
            <p className="mt-2 text-sm font-medium text-slate-600">Les offres archivées apparaîtront ici automatiquement.</p>
          </div>
        ) : (
          offers.map((offer) => <OfferCard key={offer.id} offer={offer} />)
        )}
      </section>
    </div>
  );
}
