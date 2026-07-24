from __future__ import annotations

import os
import smtplib
from dataclasses import dataclass
from datetime import datetime, timezone
from email.message import EmailMessage
from html import escape
from pathlib import Path
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
        mail_to = [x.strip() for x in os.getenv("SUMMARY_EMAIL_TO", "rejoignez-nous@acta.asso.fr").split(",") if x.strip()]
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


def _truncate(value: Any, max_chars: int = 120) -> str:
    text = str(value or "").strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _logo_subtype(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        return "jpeg"
    if suffix == ".png":
        return "png"
    if suffix == ".gif":
        return "gif"
    return "jpeg"


def _find_logo_path() -> Path | None:
    """Find the Acta logo without requiring a new environment variable.

    Priority:
    1. ACTA_LOGO_PATH, if explicitly provided.
    2. webapp/public/acta-logo.jpg from the current working directory.
    3. webapp/public/acta-logo.jpg from the repository root inferred from this file.
    4. the legacy uploaded/local name logo.jpg, only useful for local tests.
    """
    candidates: list[Path] = []

    env_path = os.getenv("ACTA_LOGO_PATH", "").strip()
    if env_path:
        candidates.append(Path(env_path))

    cwd = Path.cwd()
    candidates.extend(
        [
            cwd / "webapp" / "public" / "acta-logo.jpg",
            cwd / "webapp" / "public" / "acta-logo.png",
            cwd / "logo.jpg",
        ]
    )

    current_file = Path(__file__).resolve()
    for parent in current_file.parents:
        candidates.extend(
            [
                parent / "webapp" / "public" / "acta-logo.jpg",
                parent / "webapp" / "public" / "acta-logo.png",
                parent / "logo.jpg",
            ]
        )

    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


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


def _render_logo_block(inline_logo_cid: str | None) -> str:
    if inline_logo_cid:
        return f"""
        <img src="cid:{escape(inline_logo_cid)}" width="148" alt="Acta - Les instituts techniques agricoles" style="display:block;width:148px;max-width:148px;height:auto;border:0;outline:none;text-decoration:none;" />
        """
    return """
    <div style="font-size:34px;line-height:1;font-weight:900;letter-spacing:-0.06em;color:#000000;">acta</div>
    <div style="margin-top:3px;font-size:9px;line-height:1.2;font-weight:700;letter-spacing:0.2em;color:#111827;text-transform:uppercase;">Les instituts<br />techniques agricoles</div>
    """


def _render_summary_cards(summary_cards: list[tuple[str, int]], pipeline_status: str) -> str:
    accent_colors = ["#ffcd00", "#f6f3ee", "#ffffff", "#ffffff", "#e6007e", "#00a3e0", "#a9cf00", "#ffffff"]
    html_parts: list[str] = []
    for index, (label, value) in enumerate(summary_cards):
        bg = accent_colors[index % len(accent_colors)]
        text_color = "#ffffff" if bg in {"#e6007e", "#00a3e0"} else "#111827"
        muted_color = "rgba(255,255,255,0.78)" if bg in {"#e6007e", "#00a3e0"} else "#475569"
        border_color = "#111827" if index == 2 and pipeline_status == "success" else "#111827"
        html_parts.append(
            f"""
            <td width="25%" style="padding:6px;vertical-align:top;">
              <div style="background:{bg};border:1px solid {border_color};border-radius:18px;padding:16px 14px;min-height:86px;">
                <div style="font-size:11px;line-height:1.3;color:{muted_color};font-weight:800;text-transform:uppercase;letter-spacing:0.08em;">{escape(str(label))}</div>
                <div style="margin-top:8px;font-size:30px;line-height:1;font-weight:900;letter-spacing:-0.04em;color:{text_color};">{escape(str(value))}</div>
              </div>
            </td>
            """
        )

    rows: list[str] = []
    for i in range(0, len(html_parts), 4):
        rows.append(f"<tr>{''.join(html_parts[i:i + 4])}</tr>")
    return "".join(rows)


def _render_html(
    pipeline_run: dict[str, Any],
    rows: list[dict[str, Any]],
    totals: dict[str, int],
    monitoring_url: str | None,
    inline_logo_cid: str | None = None,
) -> str:
    pipeline_status = _status_normalize(_safe_str(pipeline_run, "status"))
    pipeline_color = _status_color(pipeline_status)
    pipeline_label = _status_label(pipeline_status)

    started_at = _safe_str(pipeline_run, "started_at", "created_at")
    finished_at = _safe_str(pipeline_run, "ended_at", "finished_at", "updated_at")
    trigger = _safe_str(pipeline_run, "trigger_type", "trigger", "trigger_mode", "run_type") or "github_actions"

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

    cards_html = _render_summary_cards(summary_cards, pipeline_status)

    rows_html = "".join(
        f"""
        <tr>
          <td style="padding:13px 14px;border-bottom:1px solid #ece7df;font-weight:800;color:#111827;vertical-align:top;">{escape(str(row['name']))}</td>
          <td style="padding:13px 14px;border-bottom:1px solid #ece7df;vertical-align:top;">
            <span style="display:inline-block;border:1px solid {row['status_color']};border-radius:999px;padding:4px 9px;color:{row['status_color']};font-size:12px;line-height:1;font-weight:900;white-space:nowrap;">
              {escape(row['status_dot'])} {escape(row['status_label'])}
            </span>
          </td>
          <td style="padding:13px 10px;border-bottom:1px solid #ece7df;text-align:right;font-weight:800;color:#111827;vertical-align:top;">{row['offers_found']}</td>
          <td style="padding:13px 10px;border-bottom:1px solid #ece7df;text-align:right;font-weight:800;color:#111827;vertical-align:top;">{row['offers_new']}</td>
          <td style="padding:13px 10px;border-bottom:1px solid #ece7df;text-align:right;font-weight:800;color:#111827;vertical-align:top;">{row['offers_updated']}</td>
          <td style="padding:13px 10px;border-bottom:1px solid #ece7df;text-align:right;font-weight:800;color:#111827;vertical-align:top;">{row['offers_archived']}</td>
          <td style="padding:13px 10px;border-bottom:1px solid #ece7df;text-align:right;font-weight:800;color:#111827;vertical-align:top;">{row['active_count']}</td>
          <td style="padding:13px 14px;border-bottom:1px solid #ece7df;color:#475569;vertical-align:top;line-height:1.45;">{escape(_truncate(row['message'], 120))}</td>
        </tr>
        """
        for row in rows
    )

    monitoring_block = ""
    if monitoring_url:
        monitoring_block = f"""
        <a href="{escape(monitoring_url)}" style="display:inline-block;background:#111827;color:#ffffff;text-decoration:none;padding:13px 18px;border-radius:999px;font-size:13px;line-height:1;font-weight:900;border:1px solid #111827;">
          Ouvrir le monitoring
        </a>
        """

    logo_block = _render_logo_block(inline_logo_cid)
    preheader = f"Agent Emplois ITA — statut {pipeline_label}, {totals['offers_found']} offre(s) trouvée(s), {totals['offers_new']} nouvelle(s)."

    html_doc = f"""
    <!doctype html>
    <html lang="fr">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <meta name="color-scheme" content="light" />
      <meta name="supported-color-schemes" content="light" />
      <title>Agent Emplois ITA — récap de run</title>
    </head>
    <body style="margin:0;padding:0;background:#f6f3ee;font-family:Arial,Helvetica,sans-serif;color:#111827;-webkit-text-size-adjust:100%;text-size-adjust:100%;">
      <div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;line-height:1px;font-size:1px;">
        {escape(preheader)}
      </div>

      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="width:100%;background:#f6f3ee;border-collapse:collapse;">
        <tr>
          <td align="center" style="padding:24px 12px;">
            <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="width:100%;max-width:1080px;border-collapse:separate;border-spacing:0;">
              <tr>
                <td style="padding:0;">
                  <div style="overflow:hidden;border:1px solid #111827;border-radius:28px;background:#ffffff;">
                    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="width:100%;border-collapse:collapse;">
                      <tr>
                        <td style="padding:20px 22px;border-bottom:1px solid #111827;background:#ffffff;">
                          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="width:100%;border-collapse:collapse;">
                            <tr>
                              <td align="left" style="vertical-align:middle;">
                                {logo_block}
                              </td>
                              <td align="right" style="vertical-align:middle;">
                                <span style="display:inline-block;border:1px solid #111827;border-radius:999px;background:#f6f3ee;padding:8px 12px;font-size:11px;line-height:1;font-weight:900;letter-spacing:0.12em;text-transform:uppercase;color:#111827;white-space:nowrap;">
                                  Récap quotidien
                                </span>
                              </td>
                            </tr>
                          </table>
                        </td>
                      </tr>

                      <tr>
                        <td style="padding:0;">
                          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="width:100%;border-collapse:collapse;">
                            <tr>
                              <td style="width:35%;background:#ffcd00;padding:28px 22px;border-right:1px solid #111827;vertical-align:top;">
                                <div style="font-size:12px;line-height:1;font-weight:900;letter-spacing:0.18em;text-transform:uppercase;color:#111827;">Statut global</div>
                                <div style="margin-top:18px;font-size:38px;line-height:0.95;font-weight:900;letter-spacing:-0.06em;color:#111827;">{escape(pipeline_label)}</div>
                                <div style="margin-top:14px;display:inline-block;border:1px solid {pipeline_color};border-radius:999px;background:#ffffff;padding:8px 11px;color:{pipeline_color};font-size:13px;line-height:1;font-weight:900;">
                                  {escape(_status_dot(pipeline_status))} {escape(pipeline_label)}
                                </div>
                              </td>
                              <td style="background:#ffffff;padding:28px 24px;vertical-align:top;">
                                <h1 style="margin:0;font-size:34px;line-height:0.98;font-weight:900;letter-spacing:-0.06em;color:#000000;">Agent Emplois ITA</h1>
                                <div style="margin-top:8px;font-size:18px;line-height:1.35;font-weight:800;color:#111827;">Récap de run</div>
                                <div style="margin-top:16px;font-size:14px;line-height:1.7;color:#475569;">
                                  <strong style="color:#111827;">Déclenchement :</strong> {escape(trigger)}<br />
                                  <strong style="color:#111827;">Début :</strong> {_fmt_dt_fr(started_at)}<br />
                                  <strong style="color:#111827;">Fin :</strong> {_fmt_dt_fr(finished_at)}
                                </div>
                                <div style="margin-top:18px;">{monitoring_block}</div>
                              </td>
                            </tr>
                          </table>
                        </td>
                      </tr>
                    </table>
                  </div>
                </td>
              </tr>

              <tr>
                <td style="padding:16px 0 0 0;">
                  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0" style="width:100%;border-collapse:collapse;">
                    {cards_html}
                  </table>
                </td>
              </tr>

              <tr>
                <td style="padding:16px 0 0 0;">
                  <div style="border:1px solid #111827;border-radius:24px;background:#ffffff;overflow:hidden;">
                    <div style="padding:20px 22px;border-bottom:1px solid #111827;background:#ffffff;">
                      <div style="font-size:22px;line-height:1;font-weight:900;letter-spacing:-0.04em;color:#000000;">Détail par ITA</div>
                      <div style="margin-top:6px;font-size:13px;line-height:1.5;color:#64748b;">Même contenu que le récap précédent, avec une mise en forme plus lisible.</div>
                    </div>
                    <div style="overflow-x:auto;">
                      <table role="table" width="100%" cellspacing="0" cellpadding="0" border="0" style="width:100%;min-width:860px;border-collapse:collapse;font-size:13px;line-height:1.35;">
                        <thead>
                          <tr style="background:#f6f3ee;">
                            <th style="text-align:left;padding:12px 14px;border-bottom:1px solid #111827;font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:#475569;">ITA</th>
                            <th style="text-align:left;padding:12px 14px;border-bottom:1px solid #111827;font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:#475569;">Statut</th>
                            <th style="text-align:right;padding:12px 10px;border-bottom:1px solid #111827;font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:#475569;">Trouvées</th>
                            <th style="text-align:right;padding:12px 10px;border-bottom:1px solid #111827;font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:#475569;">Nouv.</th>
                            <th style="text-align:right;padding:12px 10px;border-bottom:1px solid #111827;font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:#475569;">MAJ</th>
                            <th style="text-align:right;padding:12px 10px;border-bottom:1px solid #111827;font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:#475569;">Archivées</th>
                            <th style="text-align:right;padding:12px 10px;border-bottom:1px solid #111827;font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:#475569;">Actives</th>
                            <th style="text-align:left;padding:12px 14px;border-bottom:1px solid #111827;font-size:11px;letter-spacing:0.08em;text-transform:uppercase;color:#475569;">Info</th>
                          </tr>
                        </thead>
                        <tbody>
                          {rows_html}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </td>
              </tr>

              <tr>
                <td align="center" style="padding:16px 8px 0 8px;font-size:12px;line-height:1.5;color:#64748b;">
                  Email généré automatiquement depuis le workflow GitHub Actions de l’agent.
                </td>
              </tr>
            </table>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """
    return html_doc


def _render_text(pipeline_run: dict[str, Any], rows: list[dict[str, Any]], totals: dict[str, int], monitoring_url: str | None) -> str:
    pipeline_status = _status_label(_status_normalize(_safe_str(pipeline_run, "status")))
    started_at = _safe_str(pipeline_run, "started_at", "created_at")
    finished_at = _safe_str(pipeline_run, "ended_at", "finished_at", "updated_at")
    trigger = _safe_str(pipeline_run, "trigger_type", "trigger", "trigger_mode", "run_type") or "github_actions"

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


def _send_email(
    settings: MailSettings,
    subject: str,
    html_body: str,
    text_body: str,
    logo_path: Path | None = None,
    logo_cid: str = "acta-logo",
) -> None:
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.mail_from
    msg["To"] = ", ".join(settings.mail_to)
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    if logo_path and logo_path.is_file():
        try:
            html_part = msg.get_payload()[-1]
            html_part.add_related(
                logo_path.read_bytes(),
                maintype="image",
                subtype=_logo_subtype(logo_path),
                cid=f"<{logo_cid}>",
                filename=logo_path.name,
            )
        except Exception as exc:
            print(f"Logo Acta non intégré à l'email : {exc}")

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

    pipeline_run_id = os.getenv("PIPELINE_RUN_ID", "").strip()
    pipeline_query = client.table("pipeline_runs").select("*")
    if pipeline_run_id:
        pipeline_resp = pipeline_query.eq("id", pipeline_run_id).limit(1).execute()
    else:
        pipeline_resp = pipeline_query.order("created_at", desc=True).limit(1).execute()
    pipeline_runs = pipeline_resp.data or []
    if not pipeline_runs:
        print("Aucun pipeline_run trouvé -> aucun email envoyé.")
        return 0

    pipeline_run = pipeline_runs[0]
    rows, totals = _build_summary_rows(client, pipeline_run)

    pipeline_status = _status_normalize(_safe_str(pipeline_run, "status"))
    subject_icon = {"success": "🟢", "failed": "🔴", "running": "🟡"}.get(pipeline_status, "⚪")
    finished_at = _fmt_dt_fr(_safe_str(pipeline_run, "ended_at", "finished_at", "updated_at"))
    subject = f"{subject_icon} {settings.subject_prefix} — run {finished_at}"

    logo_path = _find_logo_path()
    logo_cid = "acta-logo"
    html_body = _render_html(
        pipeline_run,
        rows,
        totals,
        settings.monitoring_url,
        inline_logo_cid=logo_cid if logo_path else None,
    )
    text_body = _render_text(pipeline_run, rows, totals, settings.monitoring_url)

    _send_email(settings, subject, html_body, text_body, logo_path=logo_path, logo_cid=logo_cid)
    print(f"Email de synthèse envoyé à {', '.join(settings.mail_to)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
