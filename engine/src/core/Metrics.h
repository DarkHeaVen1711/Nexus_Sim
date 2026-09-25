#pragma once
#include <array>
#include <cstdint>
#include <algorithm>
#include <cmath>
#include <chrono>

namespace nexussim {
namespace core {

class LatencyHistogram {
public:
    // 0 to 100,000 microseconds (100ms) with 10us granularity for lower range and log scale for upper
    static constexpr size_t NUM_BUCKETS = 1024;
    static constexpr uint64_t MAX_TRACKED_US = 100000; // 100ms

    LatencyHistogram() {
        reset();
    }

    void reset() {
        buckets_.fill(0);
        count_ = 0;
        total_us_ = 0;
        min_us_ = UINT64_MAX;
        max_us_ = 0;
    }

    void record_us(uint64_t duration_us) {
        ++count_;
        total_us_ += duration_us;
        if (duration_us < min_us_) min_us_ = duration_us;
        if (duration_us > max_us_) max_us_ = duration_us;

        size_t bucket_idx = value_to_bucket(duration_us);
        ++buckets_[bucket_idx];
    }

    uint64_t count() const { return count_; }
    uint64_t min_us() const { return count_ == 0 ? 0 : min_us_; }
    uint64_t max_us() const { return max_us_; }
    double mean_us() const { return count_ == 0 ? 0.0 : static_cast<double>(total_us_) / count_; }

    uint64_t percentile(double p) const {
        if (count_ == 0) return 0;
        if (p >= 1.0) return max_us_;
        if (p <= 0.0) return min_us_;

        uint64_t target_rank = static_cast<uint64_t>(std::ceil(p * count_));
        uint64_t accumulated = 0;

        for (size_t i = 0; i < NUM_BUCKETS; ++i) {
            accumulated += buckets_[i];
            if (accumulated >= target_rank) {
                return bucket_to_value(i);
            }
        }
        return max_us_;
    }

private:
    std::array<uint32_t, NUM_BUCKETS> buckets_{};
    uint64_t count_{0};
    uint64_t total_us_{0};
    uint64_t min_us_{UINT64_MAX};
    uint64_t max_us_{0};

    static size_t value_to_bucket(uint64_t us) {
        if (us == 0) return 0;
        if (us >= MAX_TRACKED_US) return NUM_BUCKETS - 1;
        // Linear mapping below 10,000 us (10us per bucket, 1000 buckets)
        if (us < 10000) {
            return us / 10;
        }
        // Compressed mapping for 10ms - 100ms
        size_t excess = (us - 10000) / 4000;
        size_t idx = 1000 + excess;
        return std::min(idx, NUM_BUCKETS - 1);
    }

    static uint64_t bucket_to_value(size_t bucket) {
        if (bucket < 1000) {
            return (bucket * 10) + 5;
        }
        return 10000 + ((bucket - 1000) * 4000) + 2000;
    }
};

struct SubsystemUSEMetrics {
    double thread_utilization = 0.0;
    uint64_t queue_depth = 0;
    uint64_t queue_rejections = 0;

    double pathfinder_cache_hit_rate = 0.0;
    uint64_t pathfinder_queries = 0;
    uint64_t pathfinder_unreachable = 0;

    double quadtree_arena_utilization = 0.0;
    uint64_t quadtree_queries = 0;

    double ring_buffer_saturation = 0.0;
    uint64_t ring_buffer_drops = 0;

    uint64_t ws_backpressure_drops = 0;
};

struct EnginePerformanceSnapshot {
    double fps = 0.0;
    double avg_tick_ms = 0.0;
    double p50_tick_ms = 0.0;
    double p90_tick_ms = 0.0;
    double p95_tick_ms = 0.0;
    double p99_tick_ms = 0.0;
    double max_tick_ms = 0.0;
    SubsystemUSEMetrics use;
};

} // namespace core
} // namespace nexussim
