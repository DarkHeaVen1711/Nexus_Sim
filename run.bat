@echo off
setlocal enabledelayedexpansion

echo ============================================
echo   NexusSim Engine - Build ^& Run
echo ============================================
echo.

set PATH=C:\msys64\mingw64\bin;%PATH%

set CITY=piedmont
set AGENTS=500
set DURATION=5
set BUILD_TYPE=Release
set OD_PATH=
set DEMAND_SCALE=
set START_HOUR=8.0
set SPEED_FACTOR=0.55
set ROUTE_SPREAD=0.2
set CHAOS=0.1
set JOURNEY_PATH=
set FAST=0
set NO_WS=0

:parse_args
if "%~1"=="" goto build
if "%~1"=="--city" ( set CITY=%~2 & shift & shift & goto parse_args )
if "%~1"=="--agents" ( set AGENTS=%~2 & shift & shift & goto parse_args )
if "%~1"=="--duration" ( set DURATION=%~2 & shift & shift & goto parse_args )
if "%~1"=="--od" ( set OD_PATH=%~2 & shift & shift & goto parse_args )
if "%~1"=="--demand-scale" ( set DEMAND_SCALE=%~2 & shift & shift & goto parse_args )
if "%~1"=="--start-hour" ( set START_HOUR=%~2 & shift & shift & goto parse_args )
if "%~1"=="--speed-factor" ( set SPEED_FACTOR=%~2 & shift & shift & goto parse_args )
if "%~1"=="--route-spread" ( set ROUTE_SPREAD=%~2 & shift & shift & goto parse_args )
if "%~1"=="--chaos" ( set CHAOS=%~2 & shift & shift & goto parse_args )
if "%~1"=="--journey" ( set JOURNEY_PATH=%~2 & shift & shift & goto parse_args )
if "%~1"=="--fast" ( set FAST=1 & shift & goto parse_args )
if "%~1"=="--no-ws" ( set NO_WS=1 & shift & goto parse_args )
if "%~1"=="--debug" ( set BUILD_TYPE=Debug & shift & goto parse_args )
if "%~1"=="--dashboard-only" ( goto dashboard_only )
if "%~1"=="--help" goto show_help
if "%~1"=="-h" goto show_help
shift
goto parse_args

:show_help
echo Usage: run.bat [OPTIONS]
echo.
echo Options:
echo   --city NAME        City to run (fast/headless mode only; default: piedmont)
echo   --agents N         Number of agents (uniform mode, default: 500)
echo   --duration N       Duration in minutes (fast/headless mode only; default: 5)
echo   --od PATH          OD demand matrix (real-traffic mode; e.g. data\chicago\od_matrix.json)
echo   --demand-scale N   Scale factor for OD demand (auto if omitted)
echo   --start-hour H     Simulation start hour 0-23 (OD mode, default: 8)
echo   --speed-factor N   Congestion factor on IDM desired speeds (default: 0.55)
echo   --route-spread N   Stochastic route-choice spread 0-1 (default: 0.2)
echo   --chaos N          Lane-discipline chaos coefficient 0-1 (default: 0.1)
echo   --journey PATH     Where to write journey times CSV (default: journey_times.csv)
echo   --fast             Headless mode: no pacing, exits when sim finishes
echo   --no-ws            Disable WebSocket server (no dashboard)
echo   --debug            Build in Debug mode
echo   --dashboard-only   Start dashboard only (skip build/run)
echo   --help, -h         Show this help message
echo.
echo Examples:
echo   run.bat
echo   run.bat --city chicago --agents 2000 --duration 10
echo   run.bat --city chicago --od data\chicago\od_matrix.json --duration 60
echo   run.bat --fast --no-ws --od data\chicago\od_matrix.json --duration 60 --journey data\chicago\journey_times.csv
echo   run.bat --debug --agents 1000
echo   run.bat --dashboard-only
exit /b 0

:dashboard_only
cd dashboard
if not exist "node_modules" (
    echo Installing dashboard dependencies...
    call npm install
)
start "" cmd /c "npm run dev"
cd ..
echo Dashboard: http://localhost:5173
exit /b 0

:build
echo [1/3] Configuring CMake...
if not exist "engine\build" mkdir "engine\build"
cd engine\build
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=%BUILD_TYPE% -DENABLE_TESTING=OFF -DCMAKE_C_COMPILER=C:/msys64/mingw64/bin/gcc.exe -DCMAKE_CXX_COMPILER=C:/msys64/mingw64/bin/g++.exe
if errorlevel 1 (
    echo ERROR: CMake configuration failed!
    cd ..\..
    exit /b 1
)

echo.
echo [2/3] Building engine...
cmake --build .
if errorlevel 1 (
    echo ERROR: Build failed!
    cd ..\..
    exit /b 1
)

cd ..\..

echo.
echo [3/3] Starting dashboard...
cd dashboard
if not exist "node_modules" (
    echo Installing dashboard dependencies...
    call npm install
)
start "" cmd /c "npm run dev"
timeout /t 3 /nobreak >nul
cd ..

echo.
echo [4/4] Running simulation...
echo City: %CITY%
if "%OD_PATH%"=="" (
    echo Mode: uniform   Agents: %AGENTS%
) else (
    echo Mode: OD-driven   Matrix: %OD_PATH%
    echo Demand scale: %DEMAND_SCALE%   Start hour: %START_HOUR%
    echo Speed factor: %SPEED_FACTOR%   Route spread: %ROUTE_SPREAD%
)
echo Duration: %DURATION% min
echo.
echo Dashboard: http://localhost:5173
echo WebSocket: ws://localhost:9001
echo.
if "%FAST%"=="1" (
    echo Mode: headless -- the engine exits when the simulation finishes.
) else (
echo  NOTE: The engine idles until you pick a city on the dashboard. Selecting
echo  a city starts that simulation (agents respawn so traffic stays live),
echo  and you can switch cities anytime. --duration only applies in --fast mode.
echo  Press Ctrl+C to stop the engine.
)
echo.

set "ENGINE_ARGS=--city %CITY% --duration %DURATION%"
if "%OD_PATH%"=="" (
    set "ENGINE_ARGS=!ENGINE_ARGS! --agents %AGENTS%"
) else (
    set "ENGINE_ARGS=!ENGINE_ARGS! --od %OD_PATH%"
    if not "%DEMAND_SCALE%"=="" set "ENGINE_ARGS=!ENGINE_ARGS! --demand-scale %DEMAND_SCALE%"
    set "ENGINE_ARGS=!ENGINE_ARGS! --start-hour %START_HOUR% --speed-factor %SPEED_FACTOR% --route-spread %ROUTE_SPREAD%"
)
if not "%JOURNEY_PATH%"=="" set "ENGINE_ARGS=!ENGINE_ARGS! --journey %JOURNEY_PATH%"
if not "%CHAOS%"=="" set "ENGINE_ARGS=!ENGINE_ARGS! --chaos %CHAOS%"
if "%FAST%"=="1" set "ENGINE_ARGS=!ENGINE_ARGS! --fast"
if "%NO_WS%"=="1" set "ENGINE_ARGS=!ENGINE_ARGS! --no-ws"

echo Engine: engine\build\engine.exe %ENGINE_ARGS%
echo.
engine\build\engine.exe %ENGINE_ARGS%
if errorlevel 1 (
    echo ERROR: Simulation failed!
    exit /b 1
)

echo.
echo ============================================
echo   Simulation complete!
echo ============================================
endlocal
