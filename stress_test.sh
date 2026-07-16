#!/bin/bash
set -e

BUILD_DIR="engine/build"
CITY="${1:-chicago}"
AGENTS="${2:-20000}"
DURATION="${3:-10}"

echo "=== NexusSim Stress Test ==="
echo "City: $CITY | Agents: $AGENTS | Duration: ${DURATION}min"

cd "$(dirname "$0")"
mkdir -p "$BUILD_DIR" && cd "$BUILD_DIR"
cmake .. -DCMAKE_BUILD_TYPE=Release
cmake --build . -j$(nproc)

echo ""
echo "--- Running simulation ---"
./engine --city "$CITY" --agents "$AGENTS" --duration "$DURATION"

echo ""
echo "--- Valgrind memory check ---"
if command -v valgrind &>/dev/null; then
    valgrind --leak-check=full --show-leak-kinds=all \
             --error-exitcode=1 --track-origins=yes \
             ./engine --city "$CITY" --agents "$AGENTS" --duration 1
    echo "Valgrind: PASS (no leaks)"
else
    echo "Valgrind not found — skipping memory check"
    echo "Install valgrind and re-run for memory verification"
fi
