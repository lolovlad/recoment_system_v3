# Проверка ЛР4: OpenAPI, POST рекомендаций, опрос GET до SUCCESS.
param(
  [string]$BaseUrl = "http://127.0.0.1:8000",
  [int]$UserId = 1,
  [int]$TimeoutSec = 60
)

$ErrorActionPreference = "Stop"

Write-Host "[ЛР4] Базовый URL: $BaseUrl"

Write-Host "[ЛР4] Проверка OpenAPI..."
try {
  $null = Invoke-RestMethod -Uri "$BaseUrl/openapi.json" -Method Get -TimeoutSec 10
} catch {
  Write-Host "ОШИБКА: API недоступен. Запустите docker compose или uvicorn + worker + redis."
  exit 1
}
Write-Host "  OK: /openapi.json"

$body = @{ user_id = $UserId } | ConvertTo-Json
Write-Host "[ЛР4] POST /api/v1/recommendations/generate_for_user ..."
$resp = Invoke-RestMethod -Uri "$BaseUrl/api/v1/recommendations/generate_for_user" -Method Post -ContentType "application/json" -Body $body
if (-not $resp.task_id) {
  Write-Host "ОШИБКА: нет task_id в ответе"
  exit 1
}
$taskId = $resp.task_id
Write-Host "  task_id: $taskId"

$deadline = (Get-Date).AddSeconds($TimeoutSec)
do {
  $r = Invoke-RestMethod -Uri "$BaseUrl/api/v1/recommendations/results/$taskId" -Method Get -TimeoutSec 10
  Write-Host "  status=$($r.status)"
  if ($r.status -eq "SUCCESS") {
    $preview = $r.result
    if ($preview -is [array] -and $preview.Count -gt 10) { $preview = $preview[0..9] }
    Write-Host "  result (до 10): $preview"
    Write-Host "[ЛР4] Проверка пройдена."
    exit 0
  }
  if ($r.status -eq "FAILURE") {
    Write-Host "  error: $($r.error)"
    exit 1
  }
  Start-Sleep -Milliseconds 500
} while ((Get-Date) -lt $deadline)

Write-Host "Таймаут ожидания SUCCESS."
exit 1
