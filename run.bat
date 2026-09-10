@echo off
title FloodGuard BD - Professional Dashboard
cd /d "%~dp0"
start "FloodGuard BD Server" /min cmd /c "python app.py"
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:5081
exit
