export type Offer = {
  id: string;
  source_slug: string;
  source_name: string;
  title: string;
  organization: string;
  location_text: string | null;
  contract_type: string | null;
  offer_type: string | null;
  remote_mode: string | null;
  posted_at: string | null;
  first_seen_at: string | null;
  last_seen_at: string | null;
  archived_at?: string | null;
  source_url: string;
  application_url: string | null;
  description_text?: string | null;
};

export type SourceStatus = {
  source_id: string;
  source_slug: string;
  source_name: string;
  jobs_url: string;
  source_run_id: string | null;
  started_at: string | null;
  ended_at: string | null;
  status: string | null;
  offers_found: number | null;
  offers_new: number | null;
  offers_updated: number | null;
  offers_archived: number | null;
  http_errors: number | null;
  parse_errors: number | null;
  error_message: string | null;
  metrics_json: Record<string, unknown> | null;
};

export type PipelineRun = {
  id: string;
  trigger_type: string;
  started_at: string;
  ended_at: string | null;
  status: string;
  total_sources: number;
  sources_success: number;
  sources_failed: number;
  new_offers: number;
  updated_offers: number;
  archived_offers: number;
  summary_json: Record<string, unknown>;
};
