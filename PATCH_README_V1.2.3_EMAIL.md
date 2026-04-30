PATCH V1.2.3 — Email de synthèse de fin de workflow

Contenu :
- agent/app/reporting/run_summary_email.py
- agent/app/reporting/__init__.py
- WORKFLOW_EMAIL_SNIPPET_DAILY.yml
- WORKFLOW_EMAIL_SNIPPET_MANUAL.yml

But :
- envoyer un email HTML synthétique à la fin de chaque run
- se baser sur pipeline_runs, source_runs, offers et la config locale sources.yaml
- afficher un tableau par ITA avec le statut du run et les principaux compteurs

Variables à configurer dans GitHub :
- secrets :
  - SUPABASE_URL
  - SUPABASE_SERVICE_KEY
  - SMTP_HOST
  - SMTP_PORT
  - SMTP_USERNAME
  - SMTP_PASSWORD
- vars :
  - SUMMARY_EMAIL_ENABLED=true
  - SUMMARY_EMAIL_TO=mehdi.sine@acta.asso.fr
  - SUMMARY_EMAIL_FROM=Agent Emplois ITA <noreply@votredomaine.fr>
  - SUMMARY_EMAIL_SUBJECT_PREFIX=Agent Emplois ITA
  - APP_MONITORING_URL=https://votre-webapp.vercel.app/monitoring
  - SMTP_USE_TLS=true
  - SMTP_USE_SSL=false

Notes :
- GitHub Actions n'envoie pas d'email tout seul : le runner exécute votre code Python, qui doit utiliser un relais SMTP ou une API provider.
- Le patch est volontairement SMTP générique : vous pourrez démarrer avec Gmail SMTP, puis basculer ensuite vers un provider dédié sans changer le code.
- Le step d'envoi d'email doit être ajouté en fin de workflow, avec if: always() et continue-on-error: true.
