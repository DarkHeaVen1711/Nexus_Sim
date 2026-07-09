# NexusSim

Traffic simulation engine built for macro and micro-level routing analysis.

## Core Architecture
- **Pipeline (`pipeline/`)**: Python scripts to extract, clean, and enrich OpenStreetMap (OSM) data into a standard graph representation.
- **Engine (`engine/`)**: High-performance C++ simulator that loads the graph geometry.

## Quickstart

### 1. Generate City Graph
To fetch and process a city's road network, run the pipeline scripts in order:

```bash
cd pipeline
pip install -r requirements.txt # Make sure dependencies like osmnx are installed

# Run the pipeline (e.g. for Piedmont)
python src/download.py --city piedmont
python src/clean.py --city piedmont
python src/lanes.py --city piedmont
python src/zones.py --city piedmont
python src/export.py --city piedmont
```
*Note: Available cities are configured in `pipeline/cities.yaml`.*

### 2. Run the C++ Engine
Once the graph is generated, you can build and run the C++ engine:

```bash
cd engine
mkdir build && cd build
cmake ..
cmake --build .

# Run the engine
./engine --city piedmont
```

## Tool Versions (Pinned)
- CMake >= 3.25
- Python >= 3.11
- npm >= 9
- React 18
- TailwindCSS 3
