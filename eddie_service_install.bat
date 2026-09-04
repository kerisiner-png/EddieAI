@echo off
setlocal

set "PYEXE=python"
set "SVC_NAME=EddieAI"

echo.
echo ============================================
echo  EddieAI Persistent Runtime - Service Utils
echo ============================================
echo.
echo Usage:
echo   %~nx0 install    - register and start the service
echo   %~nx0 start      - start the service
echo   %~nx0 stop       - stop the service
echo   %~nx0 restart    - restart the service
echo   %~nx0 status     - show service status
echo   %~nx0 uninstall  - stop and remove the service
echo.

if "%1"=="install" goto install
if "%1"=="start" goto start
if "%1"=="stop" goto stop
if "%1"=="restart" goto restart
if "%1"=="status" goto status
if "%1"=="uninstall" goto uninstall

echo Unknown command: %1
echo.
exit /b 1

:install
echo Registering service %SVC_NAME% ...
"%PYEXE%" -m pywin32_postinstall -install
"%PYEXE%" "core\eddie_service.py" install
"%PYEXE%" "core\eddie_service.py" start
echo Service installed and started.
exit /b 0

:start
"%PYEXE%" "core\eddie_service.py" start
exit /b 0

:stop
"%PYEXE%" "core\eddie_service.py" stop
exit /b 0

:restart
"%PYEXE%" "core\eddie_service.py" stop
timeout /t 2 /nobreak >nul
"%PYEXE%" "core\eddie_service.py" start
exit /b 0

:status
sc query %SVC_NAME%
exit /b 0

:uninstall
"%PYEXE%" "core\eddie_service.py" stop
"%PYEXE%" "core\eddie_service.py" remove
echo Service removed.
exit /b 0
