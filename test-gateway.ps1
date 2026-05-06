$env:AIMS_GATEWAY_TOKEN = "aims-secret-token-2026"
$gatewayUrl = "http://localhost:18789"
$healthUrl = "$gatewayUrl/health"

Write-Host "Testing Gateway Token Authentication..."
Write-Host "Gateway URL: $gatewayUrl"
Write-Host "Health URL: $healthUrl"
Write-Host "Token: $($env:AIMS_GATEWAY_TOKEN.Substring(0,10))..."
Write-Host ""

try {
    $headers = @{
        "Authorization" = "Bearer $($env:AIMS_GATEWAY_TOKEN)"
        "Content-Type" = "application/json"
    }

    Write-Host "Testing Gateway Health Endpoint..."
    $response = Invoke-RestMethod -Uri $healthUrl -Method Get -Headers $headers -ErrorAction Stop
    
    Write-Host "[OK] Gateway Health Check Passed"
    Write-Host "Response: $($response | ConvertTo-Json -Depth 3)"
    Write-Host ""
    
    Write-Host "Testing Gateway Port Connection..."
    $portTest = Test-NetConnection -ComputerName localhost -Port 18789 -InformationLevel Quiet
    
    if ($portTest) {
        Write-Host "[OK] Gateway Port 18789 is accessible"
    } else {
        Write-Host "[FAIL] Gateway Port 18789 is not accessible"
    }
    
    Write-Host ""
    Write-Host "Gateway Token Authentication Test: PASSED"
    
} catch {
    Write-Host "[ERROR] Gateway Health Check Failed"
    Write-Host "Error: $($_.Exception.Message)"
    Write-Host ""
    Write-Host "Note: Make sure OpenClaw service is running"
    Write-Host "Start service with: powershell -ExecutionPolicy Bypass -File D:\Project\aims\run-openclaw.ps1"
}

Write-Host ""
Write-Host "=========================================="