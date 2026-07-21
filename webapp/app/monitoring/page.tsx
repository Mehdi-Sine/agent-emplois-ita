import RunTriggerButton from "@/components/RunTriggerButton";
import { getMonitoringPageData } from "@/lib/monitoring-data";

export const dynamic = "force-dynamic";
export const revalidate = 0;

function formatDate(value: string | null) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("fr-FR");
}

function statusClass(status: string) {
  const upper = status.toUpperCase();

  if (upper === "SUCCESS") {
    return "border-emerald-200 bg-emerald-50 text-emerald-700";
  }
  if (upper === "PARTIAL_SUCCESS") {
    return "border-amber-200 bg-amber-50 text-amber-800";
  }
  if (upper === "FAILED" || upper === "ERROR") {
    return "border-rose-200 bg-rose-50 text-rose-700";
  }

  return "border-slate-200 bg-slate-50 text-slate-700";
}

function statusLabel(status: string) {
  const upper = status.toUpperCase();
  if (upper === "SKIPPED") return "Ignoré";
  if (upper === "SUCCESS") return "OK";
  if (upper === "PARTIAL_SUCCESS") return "Partiel";
  if (upper === "FAILED" || upper === "ERROR") return "Erreur";
  return status;
}

function SummaryCard({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-3xl border border-black/10 bg-[#f6f3ee] p-5">
      <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-500">{label}</p>
      <p className="mt-3 text-2xl font-black text-black">{value}</p>
    </div>
  );
}

export default async function MonitoringPage() {
  const data = await getMonitoringPageData();

  return (
    <div className="space-y-6">
      <section className="grid gap-5 lg:grid-cols-[1.1fr_0.9fr]">
        <div className="rounded-[2rem] border border-black/10 bg-white p-6 shadow-sm sm:p-8">
          <p className="inline-flex rounded-full bg-black px-4 py-2 text-xs font-black uppercase tracking-[0.2em] text-white">
            Supervision
          </p>
          <h1 className="mt-5 text-3xl font-black tracking-tight text-black sm:text-5xl">Monitoring</h1>
          <p className="mt-4 max-w-3xl text-base font-medium leading-7 text-slate-600">
            Vue synthétique des dernières moissons et de l&apos;état des connecteurs.
          </p>

          <div className="mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <SummaryCard label="Statut" value={data.summary.status} />
            <SummaryCard label="Sources OK" value={data.summary.sourcesOk} />
            <SummaryCard label="Nouvelles offres" value={data.summary.newOffers} />
            <SummaryCard label="Archivées" value={data.summary.archivedOffers} />
          </div>
        </div>

        <div className="rounded-[2rem] border border-black/10 bg-white p-6 shadow-sm sm:p-8">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <h2 className="text-2xl font-black tracking-tight text-black">Derniers runs</h2>
              <p className="mt-1 text-sm font-medium text-slate-600">Déclenchement manuel possible.</p>
            </div>
            <RunTriggerButton label="Lancer un run" endpoint="/api/collect" />
          </div>

          <div className="mt-6 grid gap-3">
            {data.latestRuns.length === 0 ? (
              <div className="rounded-3xl border border-dashed border-black/20 bg-[#f6f3ee] p-5 text-sm font-semibold text-slate-600">
                Aucun run récent trouvé.
              </div>
            ) : (
              data.latestRuns.map((run) => (
                <article key={run.id} className="rounded-3xl border border-black/10 bg-[#f6f3ee] p-5">
                  <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <span className={`w-fit rounded-full border px-3 py-1 text-xs font-black ${statusClass(run.status)}`}>
                      {statusLabel(run.status)}
                    </span>
                    <span className="text-sm font-bold text-slate-500">{formatDate(run.createdAt)}</span>
                  </div>
                  <p className="mt-3 text-sm font-semibold text-slate-700">
                    {run.sourcesOk}/{run.sourcesTotal} sources OK · {run.newOffers} nouvelles · {run.updatedOffers} mises à jour
                  </p>
                </article>
              ))
            )}
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {data.sources.map((source) => (
          <article key={source.id} className="rounded-[1.75rem] border border-black/10 bg-white p-5 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0">
                <h3 className="truncate text-lg font-black tracking-tight text-black">{source.name}</h3>
                <p className="mt-1 text-sm font-bold text-slate-500">{source.slug}</p>
              </div>
              <span className={`shrink-0 rounded-full border px-3 py-1 text-xs font-black ${statusClass(source.status)}`}>
                {statusLabel(source.status)}
              </span>
            </div>

            <dl className="mt-5 grid grid-cols-3 gap-3 text-sm">
              <div className="rounded-2xl bg-[#f6f3ee] p-3">
                <dt className="text-xs font-bold text-slate-500">Offres</dt>
                <dd className="mt-1 font-black text-black">{source.offers}</dd>
              </div>
              <div className="rounded-2xl bg-[#f6f3ee] p-3">
                <dt className="text-xs font-bold text-slate-500">Nouvelles</dt>
                <dd className="mt-1 font-black text-black">{source.newOffers}</dd>
              </div>
              <div className="rounded-2xl bg-[#f6f3ee] p-3">
                <dt className="text-xs font-bold text-slate-500">MAJ</dt>
                <dd className="mt-1 font-black text-black">{source.updatedOffers}</dd>
              </div>
              <div className="rounded-2xl bg-[#f6f3ee] p-3">
                <dt className="text-xs font-bold text-slate-500">Archivées</dt>
                <dd className="mt-1 font-black text-black">{source.archived}</dd>
              </div>
              <div className="rounded-2xl bg-[#f6f3ee] p-3">
                <dt className="text-xs font-bold text-slate-500">HTTP</dt>
                <dd className="mt-1 font-black text-black">{source.httpErrors}</dd>
              </div>
              <div className="rounded-2xl bg-[#f6f3ee] p-3">
                <dt className="text-xs font-bold text-slate-500">Parse</dt>
                <dd className="mt-1 font-black text-black">{source.parseErrors}</dd>
              </div>
            </dl>

            <p className="mt-4 text-sm font-semibold text-slate-600">Dernier run : {formatDate(source.lastRunAt)}</p>

            <div className="mt-5 flex flex-col gap-2 sm:flex-row">
              {source.jobsUrl ? (
                <a
                  href={source.jobsUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex flex-1 items-center justify-center rounded-full border border-black px-4 py-2 text-sm font-black text-black hover:bg-black hover:text-white"
                >
                  Page source ↗
                </a>
              ) : null}
              {source.enabled ? (
                <RunTriggerButton label="Mettre à jour" endpoint={`/api/collect/${source.slug}`} compact />
              ) : null}
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
