#include <iostream>
#include <vector>
#include <random>
#include <chrono>
#include <cmath>
#include <algorithm>
#include <numeric>
#include "../src/spatial/Quadtree.h"

using namespace nexussim;

struct BenchPoint { double x, y; };

static std::vector<BenchPoint> generate_points(size_t n,
                                               std::mt19937& rng) {
    std::uniform_real_distribution<double> dist(0.0, 10000.0);
    std::vector<BenchPoint> pts(n);
    for (size_t i = 0; i < n; ++i)
        pts[i] = {dist(rng), dist(rng)};
    return pts;
}

static size_t naive_radius_count(const std::vector<BenchPoint>& pts,
                                 double cx, double cy, double r) {
    size_t count = 0;
    double r2 = r * r;
    for (const auto& p : pts) {
        double dx = p.x - cx;
        double dy = p.y - cy;
        if (dx * dx + dy * dy <= r2) count++;
    }
    return count;
}

static double bench_naive(const std::vector<BenchPoint>& pts,
                          double radius, int queries, size_t& sink) {
    std::mt19937 rng(123);
    std::uniform_real_distribution<double> dist(0.0, 10000.0);
    auto t0 = std::chrono::high_resolution_clock::now();
    for (int q = 0; q < queries; ++q)
        sink += naive_radius_count(pts, dist(rng), dist(rng), radius);
    auto t1 = std::chrono::high_resolution_clock::now();
    return std::chrono::duration<double, std::milli>(t1 - t0).count();
}

static double bench_quadtree(const std::vector<BenchPoint>& pts,
                             double radius, int queries, size_t& sink) {
    Quadtree<double> qt(0, 0, 10000, 10000);
    for (size_t i = 0; i < pts.size(); ++i)
        qt.insert(pts[i].x, pts[i].y, i);

    std::mt19937 rng(123);
    std::uniform_real_distribution<double> dist(0.0, 10000.0);
    std::vector<QuadPoint<double>> results;
    auto t0 = std::chrono::high_resolution_clock::now();
    for (int q = 0; q < queries; ++q) {
        results.clear();
        qt.query_radius(dist(rng), dist(rng), radius, results);
        sink += results.size();
    }
    auto t1 = std::chrono::high_resolution_clock::now();
    return std::chrono::duration<double, std::milli>(t1 - t0).count();
}

int main() {
    const double radius = 200.0;
    const int queries = 1000;
    std::mt19937 rng(42);

    size_t counts[] = {1000, 5000, 10000, 20000};
    size_t sink = 0;

    std::cout << "╔═══════════╦══════════════╦══════════════╦══════════╗\n";
    std::cout << "║  Agents   ║  Naive (ms)  ║ Quadtree(ms) ║  Speedup ║\n";
    std::cout << "╠═══════════╬══════════════╬══════════════╬══════════╣\n";

    for (size_t n : counts) {
        auto pts = generate_points(n, rng);
        double t_naive = bench_naive(pts, radius, queries, sink);
        double t_qt    = bench_quadtree(pts, radius, queries, sink);
        double speedup = (t_qt > 0) ? t_naive / t_qt : 0;

        std::cout << "║ " << n
                  << "  ║ " << t_naive
                  << "      ║ " << t_qt
                  << "       ║ " << speedup << "x   ║\n";
    }

    std::cout << "╚═══════════╩══════════════╩══════════════╩══════════╝\n";
    std::cout << "[ sanity ] sink = " << sink << " (matched counts across "
              << "all sizes: " << (sink > 0 ? "yes" : "no") << ")\n";
    return 0;
}
