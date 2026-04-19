import { getSupabaseAdmin } from "./supabase-admin";

type GenericRow = Record<string, any>;

export type MonitoringSummary = {
  status: string;
  sourcesOk: number;
  newOffers: number;
  archivedOffers: number;
};

export type MonitoringRun = {
  id: string;
  status: string;
  createdAt: string | null;
  sourcesOk: number;
  sourcesTotal: number;
  newOffers: number;
  updatedOffers: number;
};

export type MonitoringSourceCard = {
  id: string;
  slug: string;
  name: string;
  jobsUrl: string | null;
  enabled: boolean;
  status: string;
  offers: number;
  archived: number;
  newOffers: number;
  updatedOffers: number;
  httpErrors: number;
  parseErrors: number;
  lastRunAt: string | null;
};

export type MonitoringPageData = {
  summary: MonitoringSummary;
  latestRuns: MonitoringRun[];
  sources: MonitoringSourceCard[];
};

function pickString(row: GenericRow, keys: string[]): string | null {
  for (const key of keys) {
    const value = row?.[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }
  return null;
}

function pickNumber(row: GenericRow, keys: string[]): number {
  for (const key of keys) {
    const value = row?.[key];
    if (typeof value === "number" && Number.isFinite(value)) {
      return value;
    }
    if (typeof value === "string" && value.trim() !== "" && !Number.isNaN(Number(value))) {
      return Number(value);
    }
  }
  return 0;
}

function pickDate(row: GenericRow, keys: string[]): string | null {
  for (const key of keys) {
    const value = row?.[key];
    if (typeof value === "string" && value.trim()) {
      return value;
    }
  }
  return null;
}

function mergeStatusBySource(
  source: GenericRow,
  statusRows: GenericRow[],
  activeCounts: Map<string, number>,
  archivedCounts: Map<string, number>,
): MonitoringSourceCard {
  const sourceId = String(source.id);
  const slug = pickString(source, ["slug"]) ?? sourceId;
  const status = statusRows.find((row) => {
    const rowSourceId = pickString(row, ["source_id"]);
    const rowSlug = pickString(row, ["source_slug", "slug"]);
    return rowSourceId === sourceId || rowSlug === slug;
  });

  return {
    id: sourceId,
    slug,
    name: pickString(source, ["name", "source_name"]) ?? slug,
    jobsUrl: pickString(source, ["jobs_url", "site_url"]),
    enabled: source.enabled !== false,
    status: pickString(status ?? {}, ["status", "run_status"]) ?? "UNKNOWN",
    offers: activeCounts.get(sourceId) ?? 0,
    archived: archivedCounts.get(sourceId) ?? 0,
    newOffers: pickNumber(status ?? {}, [
      "new_offers",
      "offers_new",
      "new_count",
      "newly_created",
    ]),
    updatedOffers: pickNumber(status ?? {}, [
      "updated_offers",
      "offers_updated",
      "updated_count",
      "updated",
    ]),
    httpErrors: pickNumber(status ?? {}, ["http_errors", "errors_http"]),
    parseErrors: pickNumber(status ?? {}, ["parse_errors", "errors_parse"]),
    lastRunAt: pickDate(status ?? {}, [
      "run_started_at",
      "started_at",
      "created_at",
      "last_run_at",
      "updated_at",
    ]),
  };
}

function buildOfferCounters(offerRows: GenericRow[]) {
  const activeCounts = new Map<string, number>();
  const archivedCounts = new Map<string, number>();

  for (const row of offerRows) {
    const sourceId = String(row.source_id);
    const isActive = row.is_active === true;
    const isArchived = row.archived_at !== null && row.archived_at !== undefined;

    if (isActive) {
      activeCounts.set(sourceId, (activeCounts.get(sourceId) ?? 0) + 1);
    }
    if (!isActive && isArchived) {
      archivedCounts.set(sourceId, (archivedCounts.get(sourceId) ?? 0) + 1);
    }
  }

  return { activeCounts, archivedCounts };
}

function normalizeLatestRuns(rows: GenericRow[]): MonitoringRun[] {
  return rows.map((row) => {
    const summary = row.summary && typeof row.summary === "object" ? row.summary : {};

    const sourcesOk = pickNumber(row, ["sources_ok", "ok_sources"]) || pickNumber(summary, ["sources_ok", "ok_sources"]);
    const sourcesTotal =
      pickNumber(row, ["sources_total", "total_sources"]) ||
      pickNumber(summary, ["sources_total", "total_sources"]);
    const newOffers =
      pickNumber(row, ["new_offers", "offers_new"]) ||
      pickNumber(summary, ["new_offers", "offers_new"]);
    const updatedOffers =
      pickNumber(row, ["updated_offers", "offers_updated"]) ||
      pickNumber(summary, ["updated_offers", "offers_updated"]);

    return {
      id: String(row.id ?? Math.random().toString(36).slice(2)),
      status: pickString(row, ["status"]) ?? "UNKNOWN",
      createdAt: pickDate(row, ["started_at", "created_at", "finished_at"]),
      sourcesOk,
      sourcesTotal,
      newOffers,
      updatedOffers,
    };
  });
}

function buildSummary(latestRun: MonitoringRun | undefined, sourceCards: MonitoringSourceCard[]): MonitoringSummary {
  const status = latestRun?.status ?? "UNKNOWN";
  const sourcesOk = sourceCards.filter((s) => s.status === "SUCCESS").length;
  const newOffers = latestRun?.newOffers ?? 0;
  const archivedOffers = sourceCards.reduce((sum, s) => sum + s.archived, 0);

  return {
    status,
    sourcesOk,
    newOffers,
    archivedOffers,
  };
}

export async function getMonitoringPageData(): Promise<MonitoringPageData> {
  const supabase = getSupabaseAdmin();

  const [sourcesRes, statusRes, runsRes, offersRes] = await Promise.all([
    supabase.from("sources").select("*").order("name", { ascending: true }),
    supabase.from("v_source_latest_status").select("*"),
    supabase.from("pipeline_runs").select("*").order("created_at", { ascending: false }).limit(3),
    supabase.from("offers").select("source_id,is_active,archived_at"),
  ]);

  if (sourcesRes.error) {
    throw new Error(`Failed to load sources: ${sourcesRes.error.message}`);
  }
  if (statusRes.error) {
    throw new Error(`Failed to load v_source_latest_status: ${statusRes.error.message}`);
  }
  if (runsRes.error) {
    throw new Error(`Failed to load pipeline_runs: ${runsRes.error.message}`);
  }
  if (offersRes.error) {
    throw new Error(`Failed to load offers: ${offersRes.error.message}`);
  }

  const sources = sourcesRes.data ?? [];
  const statusRows = statusRes.data ?? [];
  const runRows = runsRes.data ?? [];
  const offerRows = offersRes.data ?? [];

  const { activeCounts, archivedCounts } = buildOfferCounters(offerRows);

  const sourceCards = sources.map((source) =>
    mergeStatusBySource(source, statusRows, activeCounts, archivedCounts),
  );

  const latestRuns = normalizeLatestRuns(runRows);
  const summary = buildSummary(latestRuns[0], sourceCards);

  return {
    summary,
    latestRuns,
    sources: sourceCards,
  };
}
