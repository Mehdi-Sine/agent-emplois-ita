"use client";

import Link from "next/link";
import type { ReactNode } from "react";
import { useMemo, useState } from "react";
import type { TypologyProfile } from "@/types";

function Chip({ children }: { children: ReactNode }) {
  return <span className="rounded-full border border-black/10 bg-white px-3 py-1 text-xs font-black text-slate-700">{children}</span>;
}

function ListBlock({ title, items, accent }: { title: string; items: string[]; accent: string }) {
  return (
    <div className="rounded-3xl border border-black/10 bg-white p-4 shadow-sm">
      <h4 className="text-sm font-black uppercase tracking-[0.16em] text-slate-500">{title}</h4>
      <ul className="mt-3 space-y-2 text-sm font-semibold leading-6 text-slate-700">
        {items.map((item) => (
          <li key={item} className="flex gap-2">
            <span className={`mt-2 h-2 w-2 shrink-0 rounded-full ${accent}`} />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function TypologyMindMap({ profiles }: { profiles: TypologyProfile[] }) {
  const [openProfiles, setOpenProfiles] = useState<Set<string>>(() => new Set(profiles.slice(0, 3).map((profile) => profile.id)));
  const totalOffers = useMemo(() => profiles.reduce((sum, profile) => sum + profile.count, 0), [profiles]);

  function toggle(profileId: string) {
    setOpenProfiles((current) => {
      const next = new Set(current);
      if (next.has(profileId)) {
        next.delete(profileId);
      } else {
        next.add(profileId);
      }
      return next;
    });
  }

  function expandAll() {
    setOpenProfiles(new Set(profiles.map((profile) => profile.id)));
  }

  function collapseAll() {
    setOpenProfiles(new Set());
  }

  return (
    <section className="rounded-[2rem] border border-black/10 bg-[#f6f3ee] p-4 shadow-sm sm:p-6">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div>
          <p className="inline-flex rounded-full bg-black px-4 py-2 text-xs font-black uppercase tracking-[0.2em] text-white">
            Mind map interactive
          </p>
          <h2 className="mt-4 text-2xl font-black tracking-tight text-black sm:text-4xl">Typologie des profils ITA</h2>
          <p className="mt-2 max-w-3xl text-sm font-semibold leading-6 text-slate-600">
            Cliquez sur une branche pour déployer les compétences, missions, activités, formations types et exemples d'offres rattachées.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button onClick={expandAll} className="rounded-full bg-black px-4 py-2 text-sm font-black text-white hover:bg-slate-800" type="button">
            Tout déployer
          </button>
          <button onClick={collapseAll} className="rounded-full border border-black px-4 py-2 text-sm font-black text-black hover:bg-white" type="button">
            Tout replier
          </button>
        </div>
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-[280px_1fr]">
        <div className="relative flex min-h-56 items-center justify-center rounded-[2rem] border border-black/10 bg-white p-6 text-center shadow-sm">
          <div className="absolute -right-6 top-1/2 hidden h-px w-6 bg-black/20 xl:block" />
          <div>
            <div className="mx-auto flex h-24 w-24 items-center justify-center rounded-full bg-[#ffcd00] text-4xl font-black text-black shadow-inner">
              {totalOffers}
            </div>
            <h3 className="mt-4 text-xl font-black text-black">Offres analysées</h3>
            <p className="mt-2 text-sm font-semibold leading-6 text-slate-600">Actives et archivées, regroupées par signaux détectés dans les intitulés, descriptifs et métadonnées.</p>
          </div>
        </div>

        <div className="space-y-4">
          {profiles.map((profile, index) => {
            const isOpen = openProfiles.has(profile.id);
            const accent = ["bg-[#e6007e]", "bg-[#00a3e0]", "bg-[#a9cf00]", "bg-[#ffcd00]"][index % 4];
            return (
              <article key={profile.id} className="relative rounded-[2rem] border border-black/10 bg-white shadow-sm">
                <div className="absolute -left-6 top-8 hidden h-px w-6 bg-black/20 xl:block" />
                <button
                  type="button"
                  onClick={() => toggle(profile.id)}
                  aria-expanded={isOpen}
                  className="flex w-full flex-col gap-4 p-5 text-left sm:flex-row sm:items-start sm:justify-between sm:p-6"
                >
                  <span className="min-w-0">
                    <span className="flex flex-wrap items-center gap-2">
                      <span className={`h-4 w-4 rounded-full ${accent}`} />
                      <span className="rounded-full bg-black px-3 py-1 text-xs font-black uppercase tracking-[0.16em] text-white">
                        Profil {index + 1}
                      </span>
                      <Chip>{profile.count} offre(s)</Chip>
                      <Chip>{profile.activeCount} active(s)</Chip>
                      <Chip>{profile.archivedCount} archivée(s)</Chip>
                    </span>
                    <span className="mt-3 block text-2xl font-black leading-tight tracking-tight text-black">{profile.label}</span>
                    <span className="mt-2 block max-w-3xl text-sm font-semibold leading-6 text-slate-600">{profile.description}</span>
                  </span>
                  <span className="rounded-full border border-black px-4 py-2 text-sm font-black text-black">
                    {isOpen ? "Replier −" : "Déployer +"}
                  </span>
                </button>

                {isOpen ? (
                  <div className="border-t border-black/10 bg-[#fbfaf8] p-5 sm:p-6">
                    <div className="grid gap-4 lg:grid-cols-2">
                      <ListBlock title="Compétences" items={profile.skills} accent={accent} />
                      <ListBlock title="Missions" items={profile.missions} accent={accent} />
                      <ListBlock title="Types d'activités" items={profile.activities} accent={accent} />
                      <ListBlock title="Formation type" items={profile.training} accent={accent} />
                    </div>

                    <div className="mt-5 grid gap-4 lg:grid-cols-3">
                      <div className="rounded-3xl border border-black/10 bg-white p-4">
                        <h4 className="text-sm font-black uppercase tracking-[0.16em] text-slate-500">Instituts représentés</h4>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {profile.sources.map((source) => <Chip key={source.label}>{source.label} · {source.count}</Chip>)}
                        </div>
                      </div>
                      <div className="rounded-3xl border border-black/10 bg-white p-4">
                        <h4 className="text-sm font-black uppercase tracking-[0.16em] text-slate-500">Contrats</h4>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {profile.contractTypes.length ? profile.contractTypes.map((item) => <Chip key={item.label}>{item.label} · {item.count}</Chip>) : <Chip>Non précisé</Chip>}
                        </div>
                      </div>
                      <div className="rounded-3xl border border-black/10 bg-white p-4">
                        <h4 className="text-sm font-black uppercase tracking-[0.16em] text-slate-500">Types d'offres</h4>
                        <div className="mt-3 flex flex-wrap gap-2">
                          {profile.offerTypes.length ? profile.offerTypes.map((item) => <Chip key={item.label}>{item.label} · {item.count}</Chip>) : <Chip>Non précisé</Chip>}
                        </div>
                      </div>
                    </div>

                    <div className="mt-5 rounded-3xl border border-black/10 bg-white p-4">
                      <h4 className="text-sm font-black uppercase tracking-[0.16em] text-slate-500">Exemples d'offres</h4>
                      <div className="mt-3 grid gap-2">
                        {profile.examples.map((example) => (
                          <Link key={example.id} href={`/offers/${example.id}`} className="rounded-2xl border border-black/10 bg-[#f6f3ee] px-4 py-3 text-sm font-bold text-black hover:border-black hover:bg-white">
                            {example.title} <span className="text-slate-500">— {example.sourceName}{example.archived ? " · archivée" : " · active"}</span>
                          </Link>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : null}
              </article>
            );
          })}
        </div>
      </div>
    </section>
  );
}
