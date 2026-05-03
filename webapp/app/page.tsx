import Image from "next/image";
import type { ReactNode } from "react";
import { OfferCard } from "@/components/offer-card";
import { getActiveOffers, getSourceSlugs } from "@/lib/queries";

type SearchParams = Promise<{
  q?: string;
  source?: string;
  offerType?: string;
  location?: string;
}>;

function FieldLabel({ children }: { children: ReactNode }) {
  return <label className="text-xs font-black uppercase tracking-[0.18em] text-slate-500">{children}</label>;
}

export default async function HomePage(props: { searchParams: SearchParams }) {
  const searchParams = await props.searchParams;
  const [offers, sources] = await Promise.all([
    getActiveOffers(searchParams),
    getSourceSlugs(),
  ]);

  const activeFilters = [searchParams.q, searchParams.source, searchParams.offerType, searchParams.location].filter(Boolean).length;

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-[2rem] border border-black/10 bg-white shadow-sm">
        <div className="grid gap-0 lg:grid-cols-[0.95fr_1.05fr]">
          <div className="relative flex min-h-[280px] items-center justify-center bg-[#f6f3ee] p-8">
            <div className="absolute left-6 top-6 h-16 w-16 rounded-full bg-[#e6007e] opacity-90" />
            <div className="absolute bottom-8 left-12 h-20 w-20 rounded-full bg-[#ffcd00] opacity-90" />
            <div className="absolute right-10 top-12 h-14 w-14 rounded-full bg-[#a9cf00] opacity-90" />
            <div className="absolute bottom-8 right-16 h-16 w-16 rounded-full bg-[#00a3e0] opacity-90" />
            <div className="relative flex h-44 w-44 items-center justify-center rounded-[2rem] border border-black/10 bg-white p-5 shadow-xl sm:h-56 sm:w-56">
              <Image
                src="/acta-logo.jpg"
                alt="Logo Acta - Les instituts techniques agricoles"
                width={360}
                height={200}
                className="h-auto w-full object-contain"
                priority
              />
            </div>
          </div>

          <div className="p-6 sm:p-8 lg:p-10">
            <p className="inline-flex rounded-full bg-black px-4 py-2 text-xs font-black uppercase tracking-[0.2em] text-white">
              Réseau Acta
            </p>
            <h1 className="mt-6 max-w-2xl text-4xl font-black leading-[0.95] tracking-tight text-black sm:text-5xl lg:text-6xl">
              Acta Jobs
            </h1>
            <p className="mt-5 max-w-2xl text-lg font-medium leading-8 text-slate-700">
              Offres d&apos;emploi et de stage des instituts techniques agricoles.
            </p>
            <div className="mt-8 grid gap-3 sm:grid-cols-3">
              <div className="rounded-3xl border border-black/10 bg-[#ffcd00] p-4">
                <p className="text-3xl font-black text-black">{offers.length}</p>
                <p className="mt-1 text-sm font-bold text-black/70">offre(s) affichée(s)</p>
              </div>
              <div className="rounded-3xl border border-black/10 bg-[#f6f3ee] p-4">
                <p className="text-3xl font-black text-black">{sources.length}</p>
                <p className="mt-1 text-sm font-bold text-black/70">sources actives</p>
              </div>
              <div className="rounded-3xl border border-black/10 bg-black p-4 text-white">
                <p className="text-3xl font-black">{activeFilters}</p>
                <p className="mt-1 text-sm font-bold text-white/70">filtre(s)</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="rounded-[2rem] border border-black/10 bg-white p-5 shadow-sm sm:p-6">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h2 className="text-2xl font-black tracking-tight text-black">Trouver une offre</h2>
            <p className="mt-1 text-sm font-medium text-slate-600">
              Filtrez par institut, type d&apos;offre, localisation ou mot-clé.
            </p>
          </div>
          {activeFilters > 0 ? (
            <a href="/" className="text-sm font-black text-black underline decoration-2 underline-offset-4 hover:text-slate-600">
              Réinitialiser les filtres
            </a>
          ) : null}
        </div>

        <form className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="space-y-2">
            <FieldLabel>Mot-clé</FieldLabel>
            <input
              type="text"
              name="q"
              defaultValue={searchParams.q ?? ""}
              placeholder="Titre, métier, institut..."
              className="h-12 w-full rounded-2xl border border-black/10 bg-[#f6f3ee] px-4 text-sm font-semibold outline-none placeholder:text-slate-400 focus:border-black focus:bg-white"
            />
          </div>

          <div className="space-y-2">
            <FieldLabel>Institut</FieldLabel>
            <select
              name="source"
              defaultValue={searchParams.source ?? ""}
              className="h-12 w-full rounded-2xl border border-black/10 bg-[#f6f3ee] px-4 text-sm font-semibold outline-none focus:border-black focus:bg-white"
            >
              <option value="">Tous les ITA</option>
              {sources.map((source) => (
                <option key={source.slug} value={source.slug}>
                  {source.name}
                </option>
              ))}
            </select>
          </div>

          <div className="space-y-2">
            <FieldLabel>Type</FieldLabel>
            <select
              name="offerType"
              defaultValue={searchParams.offerType ?? ""}
              className="h-12 w-full rounded-2xl border border-black/10 bg-[#f6f3ee] px-4 text-sm font-semibold outline-none focus:border-black focus:bg-white"
            >
              <option value="">Tous les types</option>
              <option value="emploi">Emploi</option>
              <option value="stage">Stage</option>
              <option value="alternance">Alternance</option>
              <option value="thèse">Thèse</option>
            </select>
          </div>

          <div className="space-y-2">
            <FieldLabel>Lieu</FieldLabel>
            <div className="flex gap-2">
              <input
                type="text"
                name="location"
                defaultValue={searchParams.location ?? ""}
                placeholder="Ville, département..."
                className="h-12 min-w-0 flex-1 rounded-2xl border border-black/10 bg-[#f6f3ee] px-4 text-sm font-semibold outline-none placeholder:text-slate-400 focus:border-black focus:bg-white"
              />
              <button
                type="submit"
                className="h-12 rounded-2xl bg-black px-5 text-sm font-black text-white hover:bg-slate-800"
              >
                OK
              </button>
            </div>
          </div>
        </form>
      </section>

      <section className="space-y-4">
        <div className="flex items-center justify-between gap-4">
          <h2 className="text-xl font-black tracking-tight text-black">Offres actives</h2>
          <p className="rounded-full bg-white px-4 py-2 text-sm font-black text-slate-700 shadow-sm ring-1 ring-black/10">
            {offers.length} résultat(s)
          </p>
        </div>

        <div className="grid gap-4">
          {offers.length === 0 ? (
            <div className="rounded-[2rem] border border-dashed border-black/20 bg-white p-10 text-center">
              <p className="text-lg font-black text-black">Aucune offre trouvée</p>
              <p className="mt-2 text-sm font-medium text-slate-600">
                Essayez d&apos;élargir les filtres ou consultez les archives.
              </p>
            </div>
          ) : (
            offers.map((offer) => <OfferCard key={offer.id} offer={offer} />)
          )}
        </div>
      </section>
    </div>
  );
}
