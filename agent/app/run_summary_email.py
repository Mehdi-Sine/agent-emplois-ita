from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from html import escape
from typing import Any

from supabase import create_client

from app.config import load_sources_config


@dataclass(slots=True)
class MailSettings:
    enabled: bool
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_use_tls: bool
    smtp_use_ssl: bool
    mail_from: str
    mail_to: list[str]
    subject_prefix: str
    monitoring_url: str | None = None

    @classmethod
    def from_env(cls) -> "MailSettings":
        enabled = os.getenv("SUMMARY_EMAIL_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
        mail_to = [x.strip() for x in os.getenv("SUMMARY_EMAIL_TO", "").split(",") if x.strip()]
        return cls(
            enabled=enabled,
            smtp_host=os.getenv("SMTP_HOST", "").strip(),
            smtp_port=int(os.getenv("SMTP_PORT", "587").strip()),
            smtp_username=os.getenv("SMTP_USERNAME", "").strip(),
            smtp_password=os.getenv("SMTP_PASSWORD", "").strip(),
            smtp_use_tls=os.getenv("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "on"},
            smtp_use_ssl=os.getenv("SMTP_USE_SSL", "false").strip().lower() in {"1", "true", "yes", "on"},
            mail_from=os.getenv("SUMMARY_EMAIL_FROM", "Agent Emplois ITA <noreply@example.org>").strip(),
            mail_to=mail_to,
            subject_prefix=os.getenv("SUMMARY_EMAIL_SUBJECT_PREFIX", "Agent Emplois ITA").strip(),
            monitoring_url=os.getenv("APP_MONITORING_URL", "").strip() or None,
        )


def _safe_int(row: dict[str, Any], *keys: str) -> int:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except Exception:
            continue
    return 0


def _safe_str(row: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return text
    return None


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        text = str(value).replace("Z", "+00:00")
        return datetime.fromisoformat(text)
    except Exception:
        return None


def _fmt_dt(value: Any) -> str:
    dt = _parse_dt(value)
    if not dt:
        return "—"
    return dt.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")


def _fmt_dt_fr(value: Any) -> str:
    dt = _parse_dt(value)
    if not dt:
        return "—"
    return dt.strftime("%d/%m/%Y %H:%M")


def _status_normalize(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {"success", "completed", "ok", "done"}:
        return "success"
    if text in {"failed", "error", "ko"}:
        return "failed"
    if text in {"running", "in_progress"}:
        return "running"
    if text in {"skipped", "disabled"}:
        return "skipped"
    return text or "unknown"


def _status_label(status: str) -> str:
    return {
        "success": "OK",
        "failed": "Erreur",
        "running": "En cours",
        "skipped": "Ignoré",
        "unknown": "Inconnu",
    }.get(status, status.title())


def _status_color(status: str) -> str:
    return {
        "success": "#0f9d58",
        "failed": "#d93025",
        "running": "#f9ab00",
        "skipped": "#5f6368",
        "unknown": "#5f6368",
    }.get(status, "#5f6368")


def _status_dot(status: str) -> str:
    return {
        "success": "●",
        "failed": "●",
        "running": "●",
        "skipped": "●",
        "unknown": "●",
    }.get(status, "●")


def _pick_message(row: dict[str, Any]) -> str:
    for key in (
        "error_message",
        "last_error",
        "http_error",
        "parse_error",
        "message",
        "summary",
        "notes",
    ):
        value = row.get(key)
        if value:
            text = str(value).strip()
            if text:
                return text
    return "—"


def _build_summary_rows(client, pipeline_run: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int]]:
    pipeline_run_id = pipeline_run["id"]

    source_runs_resp = (
        client.table("source_runs")
        .select("*")
        .eq("pipeline_run_id", pipeline_run_id)
        .execute()
    )
    source_runs = source_runs_resp.data or []

    sources_resp = client.table("sources").select("id, slug, name, is_enabled").execute()
    db_sources = sources_resp.data or []

    offers_resp = client.table("offers").select("source_id, is_active").execute()
    offers_rows = offers_resp.data or []

    db_sources_by_id = {row["id"]: row for row in db_sources if row.get("id")}
    db_sources_by_slug = {row["slug"]: row for row in db_sources if row.get("slug")}

    active_counts: dict[str, int] = {}
    inactive_counts: dict[str, int] = {}
    for row in offers_rows:
        source_id = row.get("source_id")
        if not source_id:
            continue
        if row.get("is_active") is True:
            active_counts[source_id] = active_counts.get(source_id, 0) + 1
        else:
            inactive_counts[source_id] = inactive_counts.get(source_id, 0) + 1

    source_runs_by_slug: dict[str, dict[str, Any]] = {}
    for row in source_runs:
        source_id = row.get("source_id")
        slug = _safe_str(row, "source_slug")
        if not slug and source_id in db_sources_by_id:
            slug = db_sources_by_id[source_id].get("slug")
        if slug:
            source_runs_by_slug[slug] = row

    config_rows = load_sources_config()
    rows: list[dict[str, Any]] = []

    totals = {
        "config_total": len(config_rows),
        "enabled_total": 0,
        "run_total": len(source_runs),
        "ok_total": 0,
        "failed_total": 0,
        "offers_found": 0,
        "offers_new": 0,
        "offers_updated": 0,
        "offers_archived": 0,
    }

    for cfg in config_rows:
        slug = cfg.get("slug")
        if not slug:
            continue

        enabled = bool(cfg.get("enabled"))
        if enabled:
            totals["enabled_total"] += 1

        db_source = db_sources_by_slug.get(slug)
        source_run = source_runs_by_slug.get(slug)

        if source_run:
            status = _status_normalize(_safe_str(source_run, "status"))
            if status == "success":
                totals["ok_total"] += 1
            elif status == "failed":
                totals["failed_total"] += 1
        else:
            status = "skipped" if not enabled else "unknown"

        found = _safe_int(source_run or {}, "offers_found")
        new = _safe_int(source_run or {}, "offers_new", "offers_created")
        updated = _safe_int(source_run or {}, "offers_updated")
        archived = _safe_int(source_run or {}, "offers_archived")

        totals["offers_found"] += found
        totals["offers_new"] += new
        totals["offers_updated"] += updated
        totals["offers_archived"] += archived

        source_id = db_source.get("id") if db_source else None

        rows.append(
            {
                "slug": slug,
                "name": cfg.get("name") or (db_source.get("name") if db_source else slug.upper()),
                "enabled": enabled,
                "status": status,
                "status_label": _status_label(status),
                "status_color": _status_color(status),
                "status_dot": _status_dot(status),
                "offers_found": found,
                "offers_new": new,
                "offers_updated": updated,
                "offers_archived": archived,
                "active_count": active_counts.get(source_id, 0) if source_id else 0,
                "inactive_count": inactive_counts.get(source_id, 0) if source_id else 0,
                "message": _pick_message(source_run or {}),
            }
        )

    return rows, totals


def _render_html(pipeline_run: dict[str, Any], rows: list[dict[str, Any]], totals: dict[str, int], monitoring_url: str | None) -> str:
    pipeline_status = _status_normalize(_safe_str(pipeline_run, "status"))
    pipeline_color = _status_color(pipeline_status)
    pipeline_label = _status_label(pipeline_status)

    started_at = _safe_str(pipeline_run, "started_at", "created_at")
    finished_at = _safe_str(pipeline_run, "finished_at", "updated_at")
    trigger = _safe_str(pipeline_run, "trigger", "trigger_mode", "run_type") or "github_actions"

    summary_cards = [
        ("Sources configurées", totals["config_total"]),
        ("Sources actives", totals["enabled_total"]),
        ("Sources OK", totals["ok_total"]),
        ("Sources en erreur", totals["failed_total"]),
        ("Offres trouvées", totals["offers_found"]),
        ("Nouvelles", totals["offers_new"]),
        ("Mises à jour", totals["offers_updated"]),
        ("Archivées", totals["offers_archived"]),
    ]

    cards_html = "".join(
        f"""
        <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;padding:14px 16px;min-width:132px;">
          <div style="font-size:12px;color:#6b7280;margin-bottom:6px;">{escape(str(label))}</div>
          <div style="font-size:24px;font-weight:700;color:#111827;">{escape(str(value))}</div>
        </div>
        """
        for label, value in summary_cards
    )

    rows_html = "".join(
        f"""
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #eef2f7;font-weight:600;color:#111827;">{escape(str(row['name']))}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #eef2f7;color:{row['status_color']};font-weight:600;">
            <span>{escape(row['status_dot'])}</span> {escape(row['status_label'])}
          </td>
          <td style="padding:10px 12px;border-bottom:1px solid #eef2f7;text-align:right;">{row['offers_found']}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #eef2f7;text-align:right;">{row['offers_new']}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #eef2f7;text-align:right;">{row['offers_updated']}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #eef2f7;text-align:right;">{row['offers_archived']}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #eef2f7;text-align:right;">{row['active_count']}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #eef2f7;color:#4b5563;">{escape(row['message'])[:120]}</td>
        </tr>
        """
        for row in rows
    )

    monitoring_block = ""
    if monitoring_url:
        monitoring_block = f"""
        <a href="{escape(monitoring_url)}" style="display:inline-block;background:#111827;color:#ffffff;text-decoration:none;padding:10px 14px;border-radius:10px;font-weight:600;">
          Ouvrir le monitoring
        </a>
        """

    html_doc = f"""
    <!doctype html>
    <html lang="fr">
    <body style="margin:0;padding:0;background:#f6f8fb;font-family:Arial,Helvetica,sans-serif;color:#111827;">
      <div style="max-width:1200px;margin:0 auto;padding:24px 16px;">
        <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;padding:24px;">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:16px;flex-wrap:wrap;">
            <div>
              <div style="font-size:24px;font-weight:700;color:#111827;">Agent Emplois ITA — récap de run</div>
              <div style="margin-top:8px;font-size:14px;color:#4b5563;">
                Statut global :
                <span style="color:{pipeline_color};font-weight:700;">{escape(_status_dot(pipeline_status))} {escape(pipeline_label)}</span>
              </div>
              <div style="margin-top:8px;font-size:13px;color:#6b7280;">
                Déclenchement : {escape(trigger)} · Début : {_fmt_dt_fr(started_at)} · Fin : {_fmt_dt_fr(finished_at)}
              </div>
            </div>
            <div>{monitoring_block}</div>
          </div>
        </div>

        <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:16px;">
          {cards_html}
        </div>

        <div style="background:#ffffff;border:1px solid #e5e7eb;border-radius:16px;padding:20px;margin-top:16px;">
          <div style="font-size:18px;font-weight:700;color:#111827;margin-bottom:12px;">Détail par ITA</div>
          <table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead>
              <tr style="background:#f9fafb;">
                <th style="text-align:left;padding:10px 12px;border-bottom:1px solid #e5e7eb;">ITA</th>
                <th style="text-align:left;padding:10px 12px;border-bottom:1px solid #e5e7eb;">Statut</th>
                <th style="text-align:right;padding:10px 12px;border-bottom:1px solid #e5e7eb;">Trouvées</th>
                <th style="text-align:right;padding:10px 12px;border-bottom:1px solid #e5e7eb;">Nouv.</th>
                <th style="text-align:right;padding:10px 12px;border-bottom:1px solid #e5e7eb;">MAJ</th>
                <th style="text-align:right;padding:10px 12px;border-bottom:1px solid #e5e7eb;">Archivées</th>
                <th style="text-align:right;padding:10px 12px;border-bottom:1px solid #e5e7eb;">Actives</th>
                <th style="text-align:left;padding:10px 12px;border-bottom:1px solid #e5e7eb;">Info</th>
              </tr>
            </thead>
            <tbody>
              {rows_html}
            </tbody>
          </table>
        </div>

        <div style="font-size:12px;color:#6b7280;margin-top:12px;text-align:center;">
          Email généré automatiquement depuis le workflow GitHub Actions de l’agent.
        </div>
      </div>
    </body>
    </html>
    """
    return html_doc


def _render_text(pipeline_run: dict[str, Any], rows: list[dict[str, Any]], totals: dict[str, int], monitoring_url: str | None) -> str:
    pipeline_status = _status_label(_status_normalize(_safe_str(pipeline_run, "status")))
    started_at = _safe_str(pipeline_run, "started_at", "created_at")
    finished_at = _safe_str(pipeline_run, "finished_at", "updated_at")
    trigger = _safe_str(pipeline_run, "trigger", "trigger_mode", "run_type") or "github_actions"

    lines = [
        "Agent Emplois ITA — récap de run",
        f"Statut global : {pipeline_status}",
        f"Déclenchement : {trigger}",
        f"Début : {_fmt_dt(started_at)}",
        f"Fin : {_fmt_dt(finished_at)}",
        "",
        f"Sources configurées : {totals['config_total']}",
        f"Sources actives : {totals['enabled_total']}",
        f"Sources OK : {totals['ok_total']}",
        f"Sources en erreur : {totals['failed_total']}",
        f"Offres trouvées : {totals['offers_found']}",
        f"Nouvelles : {totals['offers_new']}",
        f"Mises à jour : {totals['offers_updated']}",
        f"Archivées : {totals['offers_archived']}",
        "",
        "Détail par ITA :",
    ]
    for row in rows:
        lines.append(
            f"- {row['name']}: {row['status_label']} | trouvées={row['offers_found']} | nouvelles={row['offers_new']} | maj={row['offers_updated']} | archivées={row['offers_archived']} | actives={row['active_count']}"
        )
    if monitoring_url:
        lines.extend(["", f"Monitoring : {monitoring_url}"])
    return "\n".join(lines)


def _send_email(settings: MailSettings, subject: str, html_body: str, text_body: str) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.mail_from
    msg["To"] = ", ".join(settings.mail_to)
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    if settings.smtp_use_ssl:
        with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
            smtp.ehlo()
            if settings.smtp_use_tls:
                smtp.starttls()
                smtp.ehlo()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)


def main() -> int:
    settings = MailSettings.from_env()
    if not settings.enabled:
        print("SUMMARY_EMAIL_ENABLED=false -> email de synthèse désactivé.")
        return 0

    if not settings.mail_to:
        print("SUMMARY_EMAIL_TO vide -> aucun destinataire, sortie sans erreur.")
        return 0

    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY", "").strip()
    if not supabase_url or not supabase_service_key:
        raise RuntimeError("SUPABASE_URL et SUPABASE_SERVICE_KEY sont requis pour générer l'email de synthèse.")

    if not settings.smtp_host:
        raise RuntimeError("SMTP_HOST est requis pour envoyer l'email de synthèse.")

    client = create_client(supabase_url, supabase_service_key)

    pipeline_resp = client.table("pipeline_runs").select("*").order("created_at", desc=True).limit(1).execute()
    pipeline_runs = pipeline_resp.data or []
    if not pipeline_runs:
        print("Aucun pipeline_run trouvé -> aucun email envoyé.")
        return 0

    pipeline_run = pipeline_runs[0]
    rows, totals = _build_summary_rows(client, pipeline_run)

    pipeline_status = _status_normalize(_safe_str(pipeline_run, "status"))
    subject_icon = {"success": "🟢", "failed": "🔴", "running": "🟡"}.get(pipeline_status, "⚪")
    finished_at = _fmt_dt_fr(_safe_str(pipeline_run, "finished_at", "updated_at"))
    subject = f"{subject_icon} {settings.subject_prefix} — run {finished_at}"

    html_body = _render_html(pipeline_run, rows, totals, settings.monitoring_url)
    text_body = _render_text(pipeline_run, rows, totals, settings.monitoring_url)

    _send_email(settings, subject, html_body, text_body)
    print(f"Email de synthèse envoyé à {', '.join(settings.mail_to)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
