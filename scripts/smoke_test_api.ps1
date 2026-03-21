param(
  [string]$BaseUrl = "http://127.0.0.1:8000"
)

$estimateUrl = "$BaseUrl/api/v1/delivery/estimate_time"
$body = @{
  distance = 12.5
  hour = 18
  day_of_week = 5
  items_count = 3
} | ConvertTo-Json

Write-Host "POST $estimateUrl"
Write-Host $body

try {
  $resp = Invoke-RestMethod -Uri $estimateUrl -Method Post -ContentType "application/json" -Body $body
  $resp | ConvertTo-Json
  $taskId = $resp.task_id
  if (-not $taskId) { throw "No task_id in response" }

  $resultUrl = "$BaseUrl/api/v1/delivery/results/$taskId"
  Write-Host "GET $resultUrl"
  $r2 = Invoke-RestMethod -Uri $resultUrl -Method Get
  $r2 | ConvertTo-Json
} catch {
  Write-Host "Request failed:"
  throw
}
