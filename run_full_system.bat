@echo off
REM ====================================================================
REM  NexusSim — Full 36-Algorithm Multi-Subject System Launcher
REM ====================================================================

echo [1/5] Launching C++ Simulation Engine on port 9001...
start "NexusSim C++ Engine" cmd /k "run.bat --city chicago --od data\chicago\od_matrix.json --duration 60"

echo [2/5] Launching CV Virtual Camera Service on port 9003...
start "NexusSim Virtual Camera" cmd /k ".venv\Scripts\python.exe ml\cv\virtual_camera_service.py"

echo [3/5] Launching NLP Chat & Incident Sidecar on port 9004...
start "NexusSim NLP Chat" cmd /k ".venv\Scripts\python.exe ml\nlp\chat_service.py"

echo [4/5] Launching Cross-Subject Event Bus on port 9005...
start "NexusSim Event Bus" cmd /k ".venv\Scripts\python.exe pipeline\src\event_bus.py"

echo [5/5] Launching Algorithm Explorer API Sidecar on port 9006...
start "NexusSim Algo Explorer API" cmd /k ".venv\Scripts\python.exe ml\sidecars\algo_explorer_service.py"

echo.
echo All 36-Algorithm Sidecars successfully started.
echo Launch dashboard via: cd dashboard ^&^& npm run dev
echo ====================================================================
