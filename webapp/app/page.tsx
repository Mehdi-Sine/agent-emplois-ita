import { OfferCard } from "@/components/offer-card";
import { getActiveOffers, getSourceSlugs } from "@/lib/queries";

type SearchParams = Promise<{
  q?: string;
  source?: string;
  offerType?: string;
  location?: string;
}>;

export default async function HomePage(props: { searchParams: SearchParams }) {
  const searchParams = await props.searchParams;
  const [offers, sources] = await Promise.all([
    getActiveOffers(searchParams),
    getSourceSlugs()
  ]);

  return (
    <div className="space-y-6">
      <section className="rounded-3xl bg-white p-5 shadow-sm ring-1 ring-slate-200 sm:p-6">
        <div className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900 sm:text-3xl">
            Offres actives
          </h1>
          <p className="max-w-3xl text-sm text-slate-600 sm:text-base">
            Consultation optimisée pour desktop et smartphone, avec filtres rapides et accès direct aux annonces d&apos;origine.
          </p>
        </div>

        <form className="mt-5 grid grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
          <input
            type="text"
            name="q"
            defaultValue={searchParams.q ?? ""}
            placeholder="Mot-clé"
            className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none ring-0 placeholder:text-slate-400 focus:border-slate-400"
          />
          <select
            name="source"
            defaultValue={searchParams.source ?? ""}
            className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-slate-400"
          >
            <option value="">Tous les ITA</option>
            {sources.map((source) => (
              <option key={source.slug} value={source.slug}>
                {source.name}
              </option>
            ))}
          </select>
          <select
            name="offerType"
            defaultValue={searchParams.offerType ?? ""}
            className="rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-slate-400"
          >
            <option value="">Tous les types</option>
            <option value="emploi">Emploi</option>
            <option value="stage">Stage</option>
            <option value="alternance">Alternance</option>
            <option value="thèse">Thèse</option>
          </select>
          <div className="flex gap-3">
            <input
              type="text"
              name="location"
              defaultValue={searchParams.location ?? ""}
              placeholder="Lieu"
              className="min-w-0 flex-1 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none placeholder:text-slate-400 focus:border-slate-400"
            />
            <button
              type="submit"
              className="rounded-2xl bg-slate-900 px-5 py-3 text-sm font-medium text-white hover:bg-slate-800"
            >
              Filtrer
            </button>
          </div>
        </form>
      </section>

      <section className="flex items-center justify-between">
        <p className="text-sm text-slate-600">{offers.length} offre(s) affichée(s)</p>
      </section>

      <section className="grid gap-4">
        {offers.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center text-slate-500">
            Aucune offre trouvée avec ces filtres.
          </div>
        ) : (
          offers.map((offer) => <OfferCard key={offer.id} offer={offer} />)
        )}
      </section>
    </div>
  );
}
