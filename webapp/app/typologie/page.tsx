import type { Metadata } from "next";
import { TypologyMindMap } from "@/components/typology-mind-map";
import { getAllOffersForTypology } from "@/lib/queries";
import { buildTypology } from "@/lib/typology";

export const metadata: Metadata = {
  title: "Typologie des profils ITA | Acta Jobs",
  description: "Mind map interactive des profils de postes observés dans les offres actives et archivées des instituts techniques agricoles.",
};

export default async function TypologyPage() {
  const offers = await getAllOffersForTypology();
  const profiles = buildTypology(offers);
  const activeOffers = offers.filter((offer) => !offer.archived_at).length;
  const archivedOffers = offers.length - activeOffers;

  return (
    <div className="space-y-8">
      <section className="overflow-hidden rounded-[2rem] border border-black/10 bg-white shadow-sm">
        <div className="grid gap-0 lg:grid-cols-[0.9fr_1.1fr]">
          <div className="relative min-h-[260px] bg-black p-8 text-white">
            <div className="absolute left-8 top-8 h-24 w-24 rounded-full bg-[#e6007e] opacity-90" />
            <div className="absolute bottom-10 left-24 h-16 w-16 rounded-full bg-[#ffcd00] opacity-90" />
            <div className="absolute right-16 top-16 h-20 w-20 rounded-full bg-[#00a3e0] opacity-90" />
            <div className="absolute bottom-12 right-10 h-24 w-24 rounded-full bg-[#a9cf00] opacity-90" />
            <div className="relative flex h-full min-h-[220px] items-center justify-center">
              <div className="rounded-[2rem] border border-white/20 bg-white/10 p-6 text-center backdrop-blur">
                <p className="text-6xl font-black tracking-tight">{profiles.length}</p>
                <p className="mt-2 text-sm font-black uppercase tracking-[0.2em] text-white/80">familles de profils</p>
              </div>
            </div>
          </div>
          <div className="p-6 sm:p-8 lg:p-10">
            <p className="inline-flex rounded-full bg-[#ffcd00] px-4 py-2 text-xs font-black uppercase tracking-[0.2em] text-black">
              Analyse base de données
            </p>
            <h1 className="mt-6 max-w-3xl text-4xl font-black leading-[0.98] tracking-tight text-black sm:text-5xl">
              Typologie des profils de poste présents dans les ITA
            </h1>
            <p className="mt-5 max-w-3xl text-base font-medium leading-8 text-slate-700">
              Cette cartographie regroupe toutes les offres actives et archivées disponibles en base par grandes familles métiers. Le classement est réalisé à partir des intitulés, descriptions et métadonnées des offres, puis enrichi avec les compétences, missions, types d'activités et formations typiques observables pour ces métiers.
            </p>
            <div className="mt-8 grid gap-3 sm:grid-cols-3">
              <div className="rounded-3xl border border-black/10 bg-[#f6f3ee] p-4">
                <p className="text-3xl font-black text-black">{offers.length}</p>
                <p className="mt-1 text-sm font-bold text-black/70">offre(s) analysée(s)</p>
              </div>
              <div className="rounded-3xl border border-black/10 bg-[#a9cf00] p-4">
                <p className="text-3xl font-black text-black">{activeOffers}</p>
                <p className="mt-1 text-sm font-bold text-black/70">offre(s) active(s)</p>
              </div>
              <div className="rounded-3xl border border-black/10 bg-black p-4 text-white">
                <p className="text-3xl font-black">{archivedOffers}</p>
                <p className="mt-1 text-sm font-bold text-white/70">offre(s) archivée(s)</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {profiles.length === 0 ? (
        <section className="rounded-[2rem] border border-dashed border-black/20 bg-white p-10 text-center">
          <p className="text-lg font-black text-black">Aucune offre disponible pour produire la typologie.</p>
          <p className="mt-2 text-sm font-medium text-slate-600">Lancez une collecte ou vérifiez la connexion Supabase.</p>
        </section>
      ) : (
        <TypologyMindMap profiles={profiles} />
      )}
    </div>
  );
}
