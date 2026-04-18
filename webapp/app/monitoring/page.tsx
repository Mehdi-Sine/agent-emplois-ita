import { SourceStatusCard } from "@/components/source-status-card";
import { getLatestPipelineRuns, getLatestSourceStatuses } from "@/lib/queries";

export default async function MonitoringPage() {
  const [sourceStatuses, pipelineRuns] = await Promise.all([
    getLatestSourceStatuses(),
    getLatestPipelineRuns()
  ]);

  const latestRun = pipelineRuns[0];

  return (
    <div className="space-y-6">
      <section className="grid gap-4 lg:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <h1 className="text-2xl font-semibold tracking-tight text-slate-900">Monitoring</h1>
          <p className="mt-2 text-sm text-slate-600">
            Vue synthétique des dernières moissons et de l&apos;état des connecteurs.
          </p>

          {latestRun ? (
            <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">
              <div className="rounded-2xl bg-slate-50 p-4">
                <p className="text-sm text-slate-500">Statut</p>
                <p className="mt-1 text-base font-semibold text-slate-900">{latestRun.status}</p>
              </div>
              <div className="rounded-2xl bg-slate-50 p-4">
                <p className="text-sm text-slate-500">Sources OK</p>
                <p className="mt-1 text-base font-semibold text-slate-900">{latestRun.sources_success}</p>
              </div>
              <div className="rounded-2xl bg-slate-50 p-4">
                <p className="text-sm text-slate-500">Nouvelles offres</p>
                <p className="mt-1 text-base font-semibold text-slate-900">{latestRun.new_offers}</p>
              </div>
              <div className="rounded-2xl bg-slate-50 p-4">
                <p className="text-sm text-slate-500">Archivées</p>
                <p className="mt-1 text-base font-semibold text-slate-900">{latestRun.archived_offers}</p>
              </div>
            </div>
          ) : (
            <p className="mt-5 text-sm text-slate-500">Aucun run disponible.</p>
          )}
        </div>

        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm sm:p-6">
          <h2 className="text-lg font-semibold text-slate-900">Derniers runs</h2>
          <div className="mt-4 space-y-3">
            {pipelineRuns.slice(0, 5).map((run) => (
              <div key={run.id} className="rounded-2xl bg-slate-50 p-4 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-medium text-slate-900">{run.status}</span>
                  <span className="text-slate-500">
                    {new Date(run.started_at).toLocaleString("fr-FR")}
                  </span>
                </div>
                <p className="mt-2 text-slate-600">
                  {run.sources_success}/{run.total_sources} sources OK · {run.new_offers} nouvelles ·{" "}
                  {run.updated_offers} mises à jour
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {sourceStatuses.map((item) => (
          <SourceStatusCard key={item.source_id} item={item} />
        ))}
      </section>
    </div>
  );
}
