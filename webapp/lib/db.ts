import { createClient } from "@supabase/supabase-js";

let singleton: ReturnType<typeof createClient> | null = null;

export function getDb() {
  if (singleton) {
    return singleton;
  }
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_KEY;

  if (!url || !key) {
    throw new Error("SUPABASE_URL et SUPABASE_SERVICE_KEY sont obligatoires.");
  }

  singleton = createClient(url, key, {
    auth: { persistSession: false, autoRefreshToken: false }
  });
  return singleton;
}
