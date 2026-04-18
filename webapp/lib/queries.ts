import { getDb } from "@/lib/db";
import type { Offer, PipelineRun, SourceStatus } from "@/types";

const DEFAULT_LIMIT = 100;

export async function getActiveOffers(searchParams: {
  q?: string;
  source?: string;
  offerType?: string;
  location?: string;
}): Promise<Offer[]> {
  const db = getDb();
  let query = db
    .from("v_active_offers")
    .select("*")
    .order("last_seen_at", { ascending: false })
    .limit(DEFAULT_LIMIT);

  if (searchParams.source) {
    query = query.eq("source_slug", searchParams.source);
  }
  if (searchParams.offerType) {
    query = query.eq("offer_type", searchParams.offerType);
  }
  if (searchParams.location) {
    query = query.ilike("location_text", `%${searchParams.location}%`);
  }
  if (searchParams.q) {
    query = query.or(
      `title.ilike.%${searchParams.q}%,organization.ilike.%${searchParams.q}%,location_text.ilike.%${searchParams.q}%`
    );
  }

  const { data, error } = await query;
  if (error) {
    throw error;
  }
  return (data ?? []) as Offer[];
}

export async function getArchivedOffers(): Promise<Offer[]> {
  const db = getDb();
  const { data, error } = await db
    .from("v_archived_offers")
    .select("*")
    .order("archived_at", { ascending: false })
    .limit(DEFAULT_LIMIT);
  if (error) {
    throw error;
  }
  return (data ?? []) as Offer[];
}

export async function getOfferById(id: string): Promise<Offer | null> {
  const db = getDb();
  const { data, error } = await db
    .from("offers")
    .select(`
      id,
      title,
      organization,
      location_text,
      contract_type,
      offer_type,
      remote_mode,
      posted_at,
      first_seen_at,
      last_seen_at,
      archived_at,
      source_url,
      application_url,
      description_text,
      sources!inner(
        slug,
        name
      )
    `)
    .eq("id", id)
    .limit(1)
    .single();

  if (error) {
    return null;
  }

  return {
    id: data.id,
    title: data.title,
    organization: data.organization,
    location_text: data.location_text,
    contract_type: data.contract_type,
    offer_type: data.offer_type,
    remote_mode: data.remote_mode,
    posted_at: data.posted_at,
    first_seen_at: data.first_seen_at,
    last_seen_at: data.last_seen_at,
    archived_at: data.archived_at,
    source_url: data.source_url,
    application_url: data.application_url,
    description_text: data.description_text,
    source_slug: data.sources.slug,
    source_name: data.sources.name
  };
}

export async function getLatestSourceStatuses(): Promise<SourceStatus[]> {
  const db = getDb();
  const { data, error } = await db
    .from("v_source_latest_status")
    .select("*")
    .order("source_name", { ascending: true });

  if (error) {
    throw error;
  }
  return (data ?? []) as SourceStatus[];
}

export async function getLatestPipelineRuns(): Promise<PipelineRun[]> {
  const db = getDb();
  const { data, error } = await db
    .from("pipeline_runs")
    .select("*")
    .order("started_at", { ascending: false })
    .limit(20);

  if (error) {
    throw error;
  }
  return (data ?? []) as PipelineRun[];
}

export async function getSourceSlugs(): Promise<Array<{ slug: string; name: string }>> {
  const db = getDb();
  const { data, error } = await db
    .from("sources")
    .select("slug,name")
    .eq("is_enabled", true)
    .order("name", { ascending: true });

  if (error) {
    throw error;
  }
  return data ?? [];
}
