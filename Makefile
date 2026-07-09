.PHONY: test demo

test:
	@echo "Running tests..."
	cd engine && mkdir -p build && cd build && cmake .. && cmake --build . && ctest --output-on-failure
	cd pipeline && python -m pytest tests/
	cd dashboard && npm run test

demo:
	@echo "NexusSim ready."
