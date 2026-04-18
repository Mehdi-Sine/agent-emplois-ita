import type { SourceStatus } from "@/types";

function statusClasses(status: string | null) {
  if (status === "SUCCESS") {
    return "bg-emerald-50 text-emerald-700 border-emerald-200";
  }
  if (status === "FAILED") {
    return "bg-rose-50 text-rose-700 border-rose-200";
  }
  return "bg-slate-50 text-slate-600 border-slate-200";
}

export function SourceStatusCard({ item }: { item: SourceStatus }) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold text-slate-900">{item.source_name}</h3>
          <p className="mt-1 text-sm text-slate-500">{item.source_slug}</p>
        </div>
        <span className={`rounded-full border px-2.5 py-1 text-xs font-medium ${statusClasses(item.status)}`}>
          {item.status ?? "n.d."}
        </span>
      </div>

      <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-3">
        <div>
          <dt className="text-slate-500">Offres</dt>
          <dd className="font-medium text-slate-900">{item.offers_found ?? 0}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Nouvelles</dt>
          <dd className="font-medium text-slate-900">{item.offers_new ?? 0}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Mises à jour</dt>
          <dd className="font-medium text-slate-900">{item.offers_updated ?? 0}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Archivées</dt>
          <dd className="font-medium text-slate-900">{item.offers_archived ?? 0}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Erreurs HTTP</dt>
          <dd className="font-medium text-slate-900">{item.http_errors ?? 0}</dd>
        </div>
        <div>
          <dt className="text-slate-500">Erreurs parse</dt>
          <dd className="font-medium text-slate-900">{item.parse_errors ?? 0}</dd>
        </div>
      </dl>

      <div className="mt-4 space-y-2 text-sm">
        <p className="text-slate-600">
          Dernier run : {item.started_at ? new Date(item.started_at).toLocaleString("fr-FR") : "n.d."}
        </p>
        {item.error_message ? (
          <p className="rounded-xl bg-rose-50 p-3 text-rose-700">{item.error_message}</p>
        ) : null}
        <a
          href={item.jobs_url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex text-sm font-medium text-slate-900 underline underline-offset-2"
        >
          Voir la page source
        </a>
      </div>
    </article>
  );
}
