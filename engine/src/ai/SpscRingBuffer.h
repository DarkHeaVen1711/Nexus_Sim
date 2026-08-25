#pragma once
// Lock-free single-producer / single-consumer ring buffer (Phase 8.4).
//
// Hands observation batches from the simulation loop (producer) to the
// inference thread (consumer) without locks: the sim loop must never stall
// on a mutex owned by the inference thread. At most one thread may push and
// one thread may pop concurrently; concurrent multi-producer/multi-consumer
// use is not supported.
//
// Memory ordering follows the classic Lamport queue: each index is written
// with release semantics by its owning thread and read with acquire by the
// other, so slot data is fully visible before the index that publishes it.

#include <array>
#include <atomic>
#include <cstddef>
#include <type_traits>

namespace nexussim {
namespace ai {

template <typename T, std::size_t Capacity>
class SpscRingBuffer {
    static_assert(Capacity > 0, "capacity must be positive");
    static_assert(std::is_move_constructible_v<T> ||
                  std::is_copy_constructible_v<T>,
                  "T must be copy or move constructible");

public:
    // Returns false when the buffer is full (the producer then decides
    // whether to drop the frame — stale observations are expendable).
    bool push(const T& value) {
        const size_t tail = tail_.load(std::memory_order_relaxed);
        if (tail - head_.load(std::memory_order_acquire) == Capacity)
            return false;
        slots_[tail % Capacity] = value;
        tail_.store(tail + 1, std::memory_order_release);
        return true;
    }

    // Returns false when the buffer is empty.
    bool pop(T& out) {
        const size_t head = head_.load(std::memory_order_relaxed);
        if (head == tail_.load(std::memory_order_acquire))
            return false;
        out = slots_[head % Capacity];
        head_.store(head + 1, std::memory_order_release);
        return true;
    }

    // Approximate size; safe to call from either thread.
    size_t size() const {
        return tail_.load(std::memory_order_acquire)
             - head_.load(std::memory_order_acquire);
    }

    bool empty() const { return size() == 0; }
    bool full() const { return size() == Capacity; }

private:
    std::array<T, Capacity> slots_{};
    alignas(64) std::atomic<size_t> head_{0}; // consumer-owned
    alignas(64) std::atomic<size_t> tail_{0}; // producer-owned
};

} // namespace ai
} // namespace nexussim
