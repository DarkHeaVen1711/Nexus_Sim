.PHONY: build run test bench clean dashboard help

CITY ?= piedmont
AGENTS ?= 500
DURATION ?= 5

help:
	@echo "NexusSim — Traffic Simulation Engine"
	@echo ""
	@echo "  make build              Build the C++ engine"
	@echo "  make run                Build and run simulation (CITY, AGENTS, DURATION)"
	@echo "  make test               Run all tests (C++, Python, JS)"
	@echo "  make bench              Build and run quadtree benchmark"
	@echo "  make dashboard          Start the React dashboard"
	@echo "  make clean              Remove build artifacts"
	@echo ""
	@echo "  Variables:"
	@echo "    CITY=piedmont    AGENTS=500    DURATION=5"
	@echo ""
	@echo "  Examples:"
	@echo "    make run CITY=piedmont AGENTS=1000 DURATION=10"
	@echo "    make run  (defaults: piedmont, 500 agents, 5 min)"

build:
	cd engine && mkdir -p build && cd build && cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release -DENABLE_TESTING=OFF && cmake --build .

run: build
	cd engine && ./build/engine --city $(CITY) --agents $(AGENTS) --duration $(DURATION)

test:
	cd engine && mkdir -p build && cd build && cmake .. -G Ninja -DENABLE_TESTING=ON && cmake --build . && ctest --output-on-failure
	cd pipeline && pip install -q -r requirements.txt && python -m pytest tests/ -v
	cd dashboard && npm install --silent && npm run test

bench:
	cd engine && mkdir -p build && cd build && cmake .. -G Ninja -DCMAKE_BUILD_TYPE=Release -DENABLE_TESTING=ON && cmake --build . && ./bench_quadtree

dashboard:
	cd dashboard && npm install && npm run dev

clean:
	rm -rf engine/build
	rm -rf dashboard/node_modules
	rm -f journey_times.csv engine/journey_times.csv
