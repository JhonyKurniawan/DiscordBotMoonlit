@echo off
title Discord Bot Dashboard

REM Activate venv and run
call .venv\Scripts\Activate.bat
python run.py

REM Deactivate on exit
deactivate
