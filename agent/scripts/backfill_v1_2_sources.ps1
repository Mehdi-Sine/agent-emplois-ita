param()

Set-Location (Join-Path $PSScriptRoot "..")

$slugs = @(
  "acta",
  "armeflhor",
  "astredhor",
  "ceva",
  "inov3pt",
  "cnpf"
)

foreach ($slug in $slugs) {
  Write-Host "=== BACKFILL $slug ==="
  .\.venv\Scripts\python.exe -m app.main_backfill_sources --source $slug
}
