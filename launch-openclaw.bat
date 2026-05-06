@echo off
chcp 65001 >nul
setlocal

cd /d D:\Project\aims

echo Starting OpenClaw Host Gateway...
echo All paths locked to D: drive, no C: drive writes
echo.

powershell -ExecutionPolicy Bypass -File "D:\Project\aims\scripts\p0\Start-AimsGatewayHost.ps1"
exit /b %errorlevel%
