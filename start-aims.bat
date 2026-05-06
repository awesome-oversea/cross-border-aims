@echo off
chcp 65001 >nul
cd /d D:\Project\aims
powershell -ExecutionPolicy Bypass -File "D:\Project\aims\start-aims.ps1"
exit /b 0