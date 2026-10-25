@echo off
cd /d "%~dp0"
py -B -u run.py
if errorlevel 1 pause
