#!/usr/bin/env bash
set -e

echo "Starting NexusSim Sidecar Microservices..."

# 1. Virtual Camera (port 9003)
python -m cv.virtual_camera_service &

# 2. NLP Chat & Incident Service (port 9004)
python -m nlp.chat_service &

# 3. Cross-Subject Event Bus (port 9005)
python -m pipeline.src.event_bus &

# 4. Algo Explorer Service (port 9006)
python -m sidecars.algo_explorer_service &

# 5. Unified Backend API Gateway (port 8000)
python -m gateway.server &

echo "All backend microservices and Gateway (port 8000) spawned. Waiting for background processes..."
wait -n
exit $?
