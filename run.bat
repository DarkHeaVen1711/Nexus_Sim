@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   NexusSim Engine - Build ^& Run
echo ============================================
echo.

set CITY=chicago
set AGENTS=500
set DURATION=5
set BUILD_TYPE=Release

:parse_args
if "%~1"=="" goto build
if "%~1"=="--city" ( set CITY=%~2 & shift & shift & goto parse_args )
if "%~1"=="--agents" ( set AGENTS=%~2 & shift & shift & goto parse_args )
if "%~1"=="--duration" ( set DURATION=%~2 & shift & shift & goto parse_args )
if "%~1"=="--debug" ( set BUILD_TYPE=Debug & shift & goto parse_args )
if "%~1"=="--help" goto show_help
if "%~1"=="-h" goto show_help
shift
goto parse_args

:show_help
echo Usage: run.bat [OPTIONS]
echo.
echo Options:
echo   --city NAME        City to simulate (default: chicago)
echo   --agents N         Number of agents (default: 500)
echo   --duration N       Duration in minutes (default: 5)
echo   --debug            Build in Debug mode
echo   --help, -h         Show this help message
echo.
echo Examples:
echo   run.bat
echo   run.bat --city chicago --agents 2000 --duration 10
echo   run.bat --debug --agents 1000
exit /b 0

:build
echo [1/3] Configuring CMake...
if not exist "engine\build" mkdir "engine\build"
cd engine\build
cmake .. -DCMAKE_BUILD_TYPE=%BUILD_TYPE%
if errorlevel 1 (
    echo ERROR: CMake configuration failed!
    cd ..\..
    exit /b 1
)

echo.
echo [2/3] Building engine...
cmake --build . --config %BUILD_TYPE%
if errorlevel 1 (
    echo ERROR: Build failed!
    cd ..\..
    exit /b 1
)

echo.
echo [3/3] Running simulation...
echo City: %CITY%
echo Agents: %AGENTS%
echo Duration: %DURATION% min
echo.
%BUILD_TYPE%\engine.exe --city %CITY% --agents %AGENTS% --duration %DURATION%
if errorlevel 1 (
    echo ERROR: Simulation failed!
    cd ..\..
    exit /b 1
)

cd ..\..
echo.
echo ============================================
echo   Simulation complete!
echo ============================================
endlocal
