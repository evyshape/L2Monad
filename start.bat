@echo off
chcp 65001 >nul
title L2Monad

net session >nul 2>&1
if %errorLevel% neq 0 (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', '\"%~f0\"' -Verb RunAs"
    exit /b
)

cd /d "%~dp0"

python --version >nul 2>&1
if %errorLevel% neq 0 (
    pause
    exit /b
)

start cmd /k "python main.py"