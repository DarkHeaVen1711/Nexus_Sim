// Phase 8.6 (US-E04): micro-benchmark for ONNX policy inference.
// Runs 1000 batched greedy calls through InferenceEngine and reports
// min / avg / p95 / max latency in milliseconds. The acceptance bar is a
// p95 below 8 ms at the default batch size on commodity hardware.

#include "ai/InferenceEngine.h"
#include <algorithm>
#include <chrono>
#include <cstdlib>
#include <iostream>
#include <numeric>
#include <random>
#include <string>
#include <vector>

namespace {

double percentile(std::vector<double>& v, double p) {
    if (v.empty()) return 0.0;
    std::sort(v.begin(), v.end());
    size_t idx = static_cast<size_t>(v.size() * p);
    return v[std::min(idx, v.size() - 1)];
}

} // namespace

int main(int argc, char** argv) {
    std::string model = "tests/fixtures/policy_toy.onnx";
    int iterations = 1000;
    size_t batch = 64;

    for (int i = 1; i < argc; ++i) {
        std::string arg(argv[i]);
        auto next = [&](const char* name) -> const char* {
            if (i + 1 >= argc) {
                std::cerr << "Missing value for " << name << "\n";
                std::exit(1);
            }
            return argv[++i];
        };
        if (arg == "--model") model = next("--model");
        else if (arg == "--iters") iterations = std::atoi(next("--iters"));
        else if (arg == "--batch") batch = std::stoul(next("--batch"));
    }

    std::cout << "NexusSim inference benchmark\n";
    std::cout << "Model: " << model << "\n";

    nexussim::ai::InferenceEngine engine;
    if (!engine.load(model)) {
        std::cerr << "Failed to load model; nothing to benchmark.\n";
        return 1;
    }
    const size_t obs_dim = engine.obs_dim();
    std::cout << "Batch: " << batch << " x obs_dim=" << obs_dim
              << ", iters: " << iterations << "\n";

    // Deterministic pseudo-random observations so runs are comparable.
    std::mt19937 rng(42);
    std::uniform_real_distribution<float> dist(0.0f, 1.0f);
    std::vector<float> obs(batch * obs_dim);
    for (auto& x : obs) x = dist(rng);

    // Warm-up (graph optimizations, arena allocation, DLL paging).
    for (int i = 0; i < 50; ++i)
        static_cast<void>(engine.batch_infer(obs, batch));

    std::vector<double> ms;
    ms.reserve(iterations);
    std::vector<int> sink;
    for (int i = 0; i < iterations; ++i) {
        auto t0 = std::chrono::steady_clock::now();
        sink = engine.batch_infer(obs, batch);
        auto t1 = std::chrono::steady_clock::now();
        if (sink.size() != batch) {
            std::cerr << "Inference returned wrong action count at iter "
                      << i << "\n";
            return 1;
        }
        ms.push_back(std::chrono::duration<double, std::milli>(t1 - t0)
                         .count());
    }

    double sum = std::accumulate(ms.begin(), ms.end(), 0.0);
    double min_ms = percentile(ms, 0.0);
    double p95 = percentile(ms, 0.95);
    double max_ms = percentile(ms, 1.0);

    std::cout << "Latency (ms): min=" << min_ms << " avg="
              << (sum / ms.size()) << " p95=" << p95
              << " max=" << max_ms << "\n";
    std::cout << ((p95 <= 8.0)
                      ? "PASS: p95 within 8ms budget"
                      : "FAIL: p95 exceeds 8ms budget")
              << "\n";
    return (p95 <= 8.0) ? 0 : 2;
}
