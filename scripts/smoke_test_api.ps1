param(
  [string]$Url = "http://127.0.0.1:8000/api/v1/delivery/estimate_time"
)

$body = @{
  distance = 12.5
  hour = 18
  day_of_week = 5
  items_count = 3
} | ConvertTo-Json

Write-Host "POST $Url"
Write-Host $body

try {
  $resp = Invoke-RestMethod -Uri $Url -Method Post -ContentType "application/json" -Body $body
  $resp | ConvertTo-Json
} catch {
  Write-Host "Request failed:"
  throw
}

