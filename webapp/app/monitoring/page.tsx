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

function statusPill(status: string) {
  const upper = status.toUpperCase();

  if (upper === "SUCCESS") {
    return { bg: "#ecfdf3", text: "#027a48", border: "#a6f4c5" };
  }
  if (upper === "PARTIAL_SUCCESS") {
    return { bg: "#fff7ed", text: "#b54708", border: "#fed7aa" };
  }
  if (upper === "FAILED" || upper === "ERROR") {
    return { bg: "#fef3f2", text: "#b42318", border: "#fecdca" };
  }

  return { bg: "#eef2f7", text: "#344054", border: "#d0d5dd" };
}

function SummaryCard({
  label,
  value,
}: {
  label: string;
  value: string | number;
}) {
  return (
    <div
      style={{
        background: "#f8fafc",
        borderRadius: 18,
        padding: 20,
        minWidth: 150,
        flex: 1,
      }}
    >
      <div style={{ fontSize: 14, color: "#667085", marginBottom: 8 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 700, color: "#0a214a" }}>{value}</div>
    </div>
  );
}

export default async function MonitoringPage() {
  const data = await getMonitoringPageData();

  return (
    <main style={{ padding: "28px 30px 50px" }}>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1.2fr 0.8fr",
          gap: 18,
          marginBottom: 28,
        }}
      >
        <section
          style={{
            background: "#ffffff",
            border: "1px solid #d9e2ec",
            borderRadius: 28,
            padding: 28,
          }}
        >
          <h1 style={{ margin: 0, fontSize: 28, color: "#0a214a" }}>Monitoring</h1>
          <p style={{ marginTop: 12, marginBottom: 26, color: "#475467", fontSize: 15 }}>
            Vue synthétique des dernières moissons et de l&apos;état des connecteurs.
          </p>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
              gap: 14,
            }}
          >
            <SummaryCard label="Statut" value={data.summary.status} />
            <SummaryCard label="Sources OK" value={data.summary.sourcesOk} />
            <SummaryCard label="Nouvelles offres" value={data.summary.newOffers} />
            <SummaryCard label="Archivées" value={data.summary.archivedOffers} />
          </div>
        </section>

        <section
          style={{
            background: "#ffffff",
            border: "1px solid #d9e2ec",
            borderRadius: 28,
            padding: 28,
          }}
        >
          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
              justifyContent: "space-between",
              gap: 16,
              marginBottom: 18,
            }}
          >
            <div>
              <h2 style={{ margin: 0, fontSize: 22, color: "#0a214a" }}>Derniers runs</h2>
            </div>
            <RunTriggerButton label="Lancer un run" endpoint="/api/collect" />
          </div>

          <div style={{ display: "grid", gap: 16 }}>
            {data.latestRuns.map((run) => (
              <div
                key={run.id}
                style={{
                  background: "#f8fafc",
                  borderRadius: 20,
                  padding: 18,
                }}
              >
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: 12,
                    alignItems: "center",
                    marginBottom: 8,
                  }}
                >
                  <span style={{ fontWeight: 700, color: "#0a214a" }}>{run.status}</span>
                  <span style={{ color: "#667085" }}>{formatDate(run.createdAt)}</span>
                </div>
                <div style={{ color: "#475467" }}>
                  {run.sourcesOk}/{run.sourcesTotal} sources OK · {run.newOffers} nouvelles ·{" "}
                  {run.updatedOffers} mises à jour
                </div>
              </div>
            ))}
          </div>
        </section>
      </div>

      <section
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
          gap: 18,
        }}
      >
        {data.sources.map((source) => {
          const pill = statusPill(source.status);

          return (
            <article
              key={source.id}
              style={{
                background: "#ffffff",
                border: "1px solid #d9e2ec",
                borderRadius: 22,
                padding: 22,
              }}
            >
              <div
                style={{
                  display: "flex",
                  alignItems: "flex-start",
                  justifyContent: "space-between",
                  gap: 12,
                  marginBottom: 10,
                }}
              >
                <div>
                  <h3 style={{ margin: 0, fontSize: 18, color: "#0a214a" }}>{source.name}</h3>
                  <div style={{ marginTop: 6, color: "#667085" }}>{source.slug}</div>
                </div>

                <span
                  style={{
                    background: pill.bg,
                    color: pill.text,
                    border: `1px solid ${pill.border}`,
                    borderRadius: 999,
                    padding: "6px 12px",
                    fontSize: 12,
                    fontWeight: 700,
                    whiteSpace: "nowrap",
                  }}
                >
                  {source.status}
                </span>
              </div>

              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
                  rowGap: 14,
                  columnGap: 16,
                  marginTop: 18,
                  marginBottom: 18,
                }}
              >
                <div>
                  <div style={{ color: "#667085", fontSize: 13 }}>Offres</div>
                  <div style={{ marginTop: 4, fontWeight: 700 }}>{source.offers}</div>
                </div>
                <div>
                  <div style={{ color: "#667085", fontSize: 13 }}>Nouvelles</div>
                  <div style={{ marginTop: 4, fontWeight: 700 }}>{source.newOffers}</div>
                </div>
                <div>
                  <div style={{ color: "#667085", fontSize: 13 }}>Mises à jour</div>
                  <div style={{ marginTop: 4, fontWeight: 700 }}>{source.updatedOffers}</div>
                </div>
                <div>
                  <div style={{ color: "#667085", fontSize: 13 }}>Archivées</div>
                  <div style={{ marginTop: 4, fontWeight: 700 }}>{source.archived}</div>
                </div>
                <div>
                  <div style={{ color: "#667085", fontSize: 13 }}>Erreurs HTTP</div>
                  <div style={{ marginTop: 4, fontWeight: 700 }}>{source.httpErrors}</div>
                </div>
                <div>
                  <div style={{ color: "#667085", fontSize: 13 }}>Erreurs parse</div>
                  <div style={{ marginTop: 4, fontWeight: 700 }}>{source.parseErrors}</div>
                </div>
              </div>

              <div style={{ color: "#475467", marginBottom: 18 }}>
                Dernier run : {formatDate(source.lastRunAt)}
              </div>

              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {source.jobsUrl ? (
                  <a
                    href={source.jobsUrl}
                    target="_blank"
                    rel="noreferrer"
                    style={{
                      color: "#0a214a",
                      textDecoration: "underline",
                      fontWeight: 500,
                      width: "fit-content",
                    }}
                  >
                    Voir la page source
                  </a>
                ) : null}

                <RunTriggerButton
                  label="Mettre à jour"
                  endpoint={`/api/collect/${source.slug}`}
                  compact
                />
              </div>
            </article>
          );
        })}
      </section>
    </main>
  );
}
