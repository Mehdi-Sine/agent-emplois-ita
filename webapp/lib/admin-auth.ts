export const ADMIN_AUTH_COOKIE = "acta_jobs_admin";
export const ADMIN_AUTH_VALUE = "authorized";

export function getAdminPassword() {
  return process.env.ADMIN_PASSWORD ?? "DirectionACTA2026";
}
