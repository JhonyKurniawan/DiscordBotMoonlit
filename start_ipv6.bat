@echo off
echo Starting Flask with IPv6 support...

REM Activate venv
call .venv\Scripts\activate.bat

REM Set environment variable
set FLASK_APP=dashboard.backend.app
set FLASK_ENV=development

REM Run with IPv6 enabled
python -c "from dashboard.backend import app; app.run(host='::', port=8080)"

pause
