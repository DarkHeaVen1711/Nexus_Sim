// Unit tests for the SPSC lock-free ring buffer (Phase 8.4), including a
// contended single-producer/single-consumer stress run.

#include "ai/SpscRingBuffer.h"
#include <gtest/gtest.h>
#include <thread>
#include <vector>

namespace {

constexpr size_t kCap = 8;

TEST(SpscRingBuffer, EmptyOnConstruction) {
    nexussim::ai::SpscRingBuffer<int, kCap> q;
    EXPECT_TRUE(q.empty());
    EXPECT_EQ(q.size(), 0u);
    int v = 0;
    EXPECT_FALSE(q.pop(v));
}

TEST(SpscRingBuffer, PushPopPreservesOrder) {
    nexussim::ai::SpscRingBuffer<int, kCap> q;
    for (int i = 0; i < 5; ++i) ASSERT_TRUE(q.push(i));
    EXPECT_EQ(q.size(), 5u);
    for (int expected = 0; expected < 5; ++expected) {
        int v = -1;
        ASSERT_TRUE(q.pop(v));
        EXPECT_EQ(v, expected);
    }
    EXPECT_TRUE(q.empty());
}

TEST(SpscRingBuffer, RejectsPushWhenFull) {
    nexussim::ai::SpscRingBuffer<int, kCap> q;
    for (size_t i = 0; i < kCap; ++i) ASSERT_TRUE(q.push(int(i)));
    EXPECT_TRUE(q.full());
    EXPECT_FALSE(q.push(99));
}

TEST(SpscRingBuffer, WrapsAroundIndefinitely) {
    nexussim::ai::SpscRingBuffer<int, 4> q;
    int v = 0;
    for (int round = 0; round < 100; ++round) {
        for (int i = 0; i < 3; ++i) ASSERT_TRUE(q.push(round * 10 + i));
        for (int i = 0; i < 3; ++i) {
            ASSERT_TRUE(q.pop(v));
            EXPECT_EQ(v, round * 10 + i);
        }
    }
}

struct MoveOnly {
    MoveOnly() : value(-1) {}
    explicit MoveOnly(int x) : value(x) {}
    MoveOnly(MoveOnly&&) = default;
    MoveOnly& operator=(MoveOnly&&) = default;
    MoveOnly(const MoveOnly&) = delete;
    MoveOnly& operator=(const MoveOnly&) = delete;
    int value;
};

TEST(SpscRingBuffer, SupportsMoveOnlyElements) {
    nexussim::ai::SpscRingBuffer<MoveOnly, 2> q;
    ASSERT_TRUE(q.push(MoveOnly(7)));
    MoveOnly out(0);
    ASSERT_TRUE(q.pop(out));
    EXPECT_EQ(out.value, 7);
}

TEST(SpscRingBuffer, ContendedProducerConsumerStress) {
    nexussim::ai::SpscRingBuffer<uint64_t, 256> q;
    constexpr uint64_t kMessages = 200000;

    std::thread producer([&q] {
        for (uint64_t i = 1; i <= kMessages; ++i)
            while (!q.push(i)) {} // spin: sim-loop style backoff
    });
    std::vector<uint64_t> received;
    received.reserve(kMessages);
    std::thread consumer([&q, &received] {
        uint64_t v = 0;
        while (received.size() < kMessages) {
            if (!q.pop(v)) continue;
            received.push_back(v);
        }
    });
    producer.join();
    consumer.join();

    ASSERT_EQ(received.size(), kMessages);
    for (uint64_t i = 0; i < kMessages; ++i)
        ASSERT_EQ(received[i], i + 1) << "sequence corrupted at " << i;
}

} // namespace
