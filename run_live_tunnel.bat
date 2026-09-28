@echo off
title CYRIS Server & Live Public Tunnel
echo ========================================================
echo   Starting CYRIS Full-Stack Server & Public Tunnel...
echo ========================================================
cd /d "%~dp0"
start "CYRIS Server" cmd /k "python start_server.py"
timeout /t 3 /nobreak >nul
echo Starting Public Cloudflare Tunnel...
cmd /k "npx --yes cloudflared tunnel --url http://localhost:8000"
