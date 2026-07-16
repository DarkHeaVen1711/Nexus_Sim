.PHONY: test demo bench stress

test:
	@echo "Running tests..."
	cd engine && mkdir -p build && cd build && cmake .. && cmake --build . && ctest --output-on-failure
	cd pipeline && python -m pytest tests/
	cd dashboard && npm run test

demo:
	@echo "NexusSim ready."

bench:
	cd engine && mkdir -p build && cd build && cmake .. && cmake --build . && ./bench_quadtree

stress:
	cd engine && mkdir -p build && cd build && cmake .. && cmake --build .
	@echo "Running 20k-agent stress test (10 min)..."
	cd engine/build && ./engine --city chicago --agents 20000 --duration 10
	@echo "Valgrind check (Linux only):"
	@echo "  valgrind --leak-check=full --error-exitcode=1 ./engine --city chicago --agents 20000 --duration 10"
