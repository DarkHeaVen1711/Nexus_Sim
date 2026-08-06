# NexusSim

Traffic simulation engine for macro and micro-level routing analysis with real-time visualization.

## Architecture

| Component | Path | Description |
|-----------|------|-------------|
| **Pipeline** | `pipeline/` | Python scripts to extract, clean, and enrich OpenStreetMap data into a graph |
| **Engine** | `engine/` | C++17 simulator with IDM car-following, A* pathfinding, quadtree spatial index |
| **Dashboard** | `dashboard/` | React + Leaflet real-time visualization connected via WebSocket |

## Prerequisites

### Windows
- [MSYS2](https://www.msys2.org/) with MinGW-w64 GCC 13+
- CMake >= 3.25 (bundled with MSYS2)
- Ninja (bundled with MSYS2)
- Python 3.11+
- Node.js 18+

Install MSYS2 toolchain:
```bash
pacman -S mingw-w64-x86_64-gcc mingw-w64-x86_64-cmake mingw-w64-x86_64-ninja
```

### Linux / macOS
- GCC 11+ or Clang 14+ with C++17 support
- CMake >= 3.25
- Python 3.11+
- Node.js 18+
- `libuv-dev` / `libuv-devel` (optional, fetched automatically if missing)

```bash
# Ubuntu/Debian
sudo apt install build-essential cmake ninja-build python3-pip nodejs npm

# macOS (Homebrew)
brew install cmake ninja python node
```

## Quick Start

```bash
git clone https://github.com/DarkHeaVen1711/Nexus_Sim.git
cd Nexus_Sim
```

### Windows (one command)
```batch
run.bat
```
This builds the engine, starts the dashboard at http://localhost:5173, and runs a 5-minute simulation with 500 agents on Piedmont.

### Linux / macOS

**1. Build and run the engine**
```bash
cd engine
mkdir build && cd build
cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release
cmake --build .
cd ../..

# Run from the engine directory (so data/ path resolves)
cd engine
./build/engine.exe --city piedmont --agents 500 --duration 5
```

**2. Start the dashboard** (in a separate terminal)
```bash
cd dashboard
npm install
npm run dev
```
Open http://localhost:5173 to see the live visualization.

### run.bat Options
```
--city NAME        City to simulate (default: piedmont)
--agents N         Number of agents (default: 500)
--duration N       Duration in minutes (default: 5)
--debug            Build in Debug mode
--dashboard-only   Start dashboard only (skip build/run)
```

## Generating New City Data

The pipeline extracts road networks from OpenStreetMap:

```bash
cd pipeline
pip install -r requirements.txt

python src/download.py --city piedmont
python src/clean.py --city piedmont
python src/lanes.py --city piedmont
python src/zones.py --city piedmont
python src/export.py --city piedmont
```

This produces `data/<city>/graph.json` which the engine loads.

## Running Tests

### C++ (GoogleTest)
```bash
cd engine
mkdir build && cd build
cmake .. -G Ninja -DENABLE_TESTING=ON
cmake --build .
ctest --output-on-failure
```

### Python (pytest)
```bash
cd pipeline
pip install -r requirements.txt
python -m pytest tests/ -v
```

### Dashboard
```bash
cd dashboard
npm install
npm run test
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Simulation engine | C++17, FlatBuffers, uWebSockets, libuv |
| Build system | CMake 3.25+, Ninja, GoogleTest |
| Data pipeline | Python 3.11+, osmnx, pyyaml |
| Dashboard | React 19, TypeScript, Vite, Leaflet |
| CI | GitHub Actions (ubuntu-latest) |

## Project Structure

```
NexusSim/
├── engine/           # C++ simulation engine
│   ├── src/
│   │   ├── agent/        # Agent system, IDM, pathfinding
│   │   ├── graph/        # Graph loader from JSON
│   │   ├── network/      # WebSocket server
│   │   └── spatial/      # Quadtree spatial index
│   ├── tests/        # GoogleTest unit tests
│   ├── bench/        # Benchmarks
│   ├── schemas/      # FlatBuffers schema
│   └── CMakeLists.txt
├── pipeline/         # Python data pipeline
│   ├── src/          # download, clean, lanes, zones, export
│   ├── tests/        # pytest tests
│   └── requirements.txt
├── dashboard/        # React + Leaflet visualization
│   ├── src/
│   └── package.json
├── data/             # City graph data (graph.json per city)
├── docs/             # Documentation (PRD, TRD, implementation plan, tech stack)
├── run.bat           # Windows one-click build & run
├── Makefile          # Unix build/run/test helpers
└── .github/workflows/ci.yml
```
